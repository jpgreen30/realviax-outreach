"""Webhooks router for Brevo and Stripe"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import logging
from app.utils.db import SessionLocal
from app.models.models import Lead, SystemEvent

logger = logging.getLogger(__name__)

router = APIRouter()

def log_event(db, event_type, source, lead_id=None, message=None, details=None):
    try:
        ev = SystemEvent(
            type=event_type,
            source=source,
            lead_id=lead_id,
            message=message,
            details=details,
        )
        db.add(ev)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
        db.rollback()

@router.post("/brevo")
async def brevo_webhook(request: Request):
    """Handle Brevo email events (opens, clicks, bounces, etc.)"""
    payload = await request.json()
    db = SessionLocal()
    try:
        events = payload if isinstance(payload, list) else [payload]
        for event in events:
            email = event.get('email', '')
            event_type = event.get('event', '')
            # Find lead by email
            leads = db.query(Lead).filter(Lead.agent_email == email).all()
            if not leads:
                # Still log the event even if unmatched
                log_event(db, f"email.{event_type}", "brevo", lead_id=None, message=f"Unmatched email {email}", details=event)
                continue
            for lead in leads:
                # Match lead_id if provided in event meta
                event_lead_id = event.get('meta', {}).get('lead_id')
                if event_lead_id and lead.id != event_lead_id:
                    continue
                if event_type == 'sent':
                    # Mark sent if not already
                    if not lead.email_sent_at:
                        lead.email_sent_at = datetime.utcnow()
                elif event_type == 'delivered':
                    pass
                elif event_type == 'open':
                    lead.email_opened = True
                    lead.email_opened_at = datetime.utcnow()
                elif event_type == 'click':
                    lead.email_clicked = True
                    lead.email_clicked_at = datetime.utcnow()
                elif event_type == 'bounce':
                    lead.status = LeadStatus.BOUNCED.value if hasattr(LeadStatus, 'BOUNCED') else 'bounced'
                elif event_type == 'blocked':
                    lead.status = LeadStatus.BOUNCED.value if hasattr(LeadStatus, 'BOUNCED') else 'bounced'
                db.commit()
                logger.info(f"Lead {lead.id} updated via Brevo webhook: {event_type}")
                log_event(db, f"email.{event_type}", "brevo", lead_id=lead.id, message=f"Email {event_type} for lead {lead.id}", details=event)
        return JSONResponse(content={'status': 'ok'})
    except Exception as e:
        logger.error(f"Brevo webhook error: {e}")
        raise HTTPException(status_code=500, detail='Webhook processing failed')
    finally:
        db.close()
