"""
Outreach tracking - logs events to database
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from database.models import (
    Base, Lead, Video, OutreachLog, LeadStatus, 
    init_db, engine as default_engine
)

logger = logging.getLogger(__name__)

class Tracker:
    def __init__(self, database_url: Optional[str] = None):
        self.engine = create_engine(database_url) if database_url else default_engine
        self.SessionLocal = init_db(self.engine)
    
    def get_or_create_lead(self, session: Session, listing_url: str, **kwargs) -> Lead:
        """Find existing lead or create new"""
        lead = session.query(Lead).filter_by(listing_url=listing_url).first()
        if not lead:
            lead = Lead(listing_url=listing_url, **kwargs)
            session.add(lead)
            session.flush()
        return lead
    
    def log_email_sent(
        self,
        listing_url: str,
        to_email: str,
        message_id: str,
        template: str,
        agent_name: str = ""
    ) -> None:
        """Record that an email was sent"""
        with self.SessionLocal() as session:
            lead = self.get_or_create_lead(session, listing_url, agent_email=to_email, agent_name=agent_name)
            lead.status = LeadStatus.EMAIL_SENT
            lead.email_sent_at = datetime.utcnow()
            lead.email_id = message_id
            
            log = OutreachLog(
                lead_id=lead.id,
                channel="email",
                template_used=template,
                message_sid=message_id,
                status="sent"
            )
            session.add(log)
            session.commit()
            logger.info(f"Tracked email sent to {to_email} for {listing_url}")
    
    def log_email_opened(self, message_id: str, opened_at: datetime) -> None:
        """Record email open event (from tracking pixel)"""
        with self.SessionLocal() as session:
            lead = session.query(Lead).filter_by(email_id=message_id).first()
            if lead:
                lead.status = LeadStatus.EMAIL_OPENED
                lead.email_opened = True
                lead.email_opened_at = opened_at
                log = session.query(OutreachLog).filter_by(message_sid=message_id).first()
                if log:
                    log.opened_at = opened_at
                    log.status = "opened"
                session.commit()
    
    def log_email_clicked(self, message_id: str, clicked_at: datetime) -> None:
        """Record email click event"""
        with self.SessionLocal() as session:
            lead = session.query(Lead).filter_by(email_id=message_id).first()
            if lead:
                lead.status = LeadStatus.EMAIL_CLICKED
                lead.email_clicked = True
                lead.email_clicked_at = clicked_at
                log = session.query(OutreachLog).filter_by(message_sid=message_id).first()
                if log:
                    log.clicked_at = clicked_at
                    log.status = "clicked"
                session.commit()
    
    def log_video_generated(
        self,
        listing_url: str,
        video_type: str,
        file_path: str,
        file_size: int,
        duration: int = 30
    ) -> Video:
        """Record video generation"""
        with self.SessionLocal() as session:
            lead = self.get_or_create_lead(session, listing_url)
            video = Video(
                lead_id=lead.id,
                video_type=video_type,
                duration=duration,
                file_path=file_path,
                file_size=file_size
            )
            session.add(video)
            session.commit()
            logger.info(f"Tracked video: {video_type} for {listing_url}")
            return video
    
    def log_conversion(
        self,
        listing_url: str,
        full_video_url: str,
        invoice_sent: bool = True
    ) -> None:
        """Record conversion to full video sale"""
        with self.SessionLocal() as session:
            lead = session.query(Lead).filter_by(listing_url=listing_url).first()
            if lead:
                lead.status = LeadStatus.CONVERTED
                lead.converted_at = datetime.utcnow()
                lead.converted_to_full_video = True
                lead.full_video_url = full_video_url
                lead.invoice_sent = invoice_sent
                session.commit()
                logger.info(f"Conversion logged for {listing_url}")
    
    def get_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get campaign metrics"""
        with self.SessionLocal() as session:
            from sqlalchemy import func, extract
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            metrics = {
                "total_leads": session.query(func.count(Lead.id)).filter(Lead.created_at >= cutoff).scalar() or 0,
                "emails_sent": session.query(func.count(OutreachLog.id)).filter(
                    OutreachLog.channel == "email",
                    OutreachLog.created_at >= cutoff
                ).scalar() or 0,
                "emails_opened": session.query(func.count(Lead.id)).filter(
                    Lead.email_opened == True,
                    Lead.email_opened_at >= cutoff
                ).scalar() or 0,
                "videos_generated": session.query(func.count(Video.id)).filter(
                    Video.created_at >= cutoff
                ).scalar() or 0,
                "conversions": session.query(func.count(Lead.id)).filter(
                    Lead.status == LeadStatus.CONVERTED,
                    Lead.converted_at >= cutoff
                ).scalar() or 0,
                "revenue": session.query(func.sum(Lead.full_video_url != None)).filter(
                    Lead.converted_at >= cutoff
                ).scalar() or 0  # Count conversions * $250
            }
            
            if metrics["emails_sent"] > 0:
                metrics["open_rate"] = metrics["emails_opened"] / metrics["emails_sent"]
            else:
                metrics["open_rate"] = 0
            
            return metrics