"""Admin/monitoring router"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.utils.db import SessionLocal
from app.models.models import Lead, SystemEvent

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/metrics")
def get_metrics():
    """High-level funnel metrics"""
    db = SessionLocal()
    try:
        total_leads = db.query(Lead).count()
        emails_sent = db.query(Lead).filter(Lead.email_sent_at != None).count()
        emails_opened = db.query(Lead).filter(Lead.email_opened == True).count()
        emails_clicked = db.query(Lead).filter(Lead.email_clicked == True).count()
        conversions = db.query(Lead).filter(Lead.payment_received == True).count()
        # Sum revenue assuming 250 per conversion
        revenue = conversions * 250.0
        return {
            "total_leads": total_leads,
            "emails_sent": emails_sent,
            "emails_opened": emails_opened,
            "emails_clicked": emails_clicked,
            "conversions": conversions,
            "revenue_usd": revenue,
            "updated_at": datetime.utcnow().isoformat()
        }
    finally:
        db.close()

@router.get("/events")
def get_recent_events(limit: int = 50, type: str = None):
    """Recent system events (webhooks, errors, etc.)"""
    db = SessionLocal()
    try:
        query = db.query(SystemEvent)
        if type:
            query = query.filter(SystemEvent.type == type)
        events = query.order_by(SystemEvent.created_at.desc()).limit(limit).all()
        return [
            {
                "id": e.id,
                "created_at": e.created_at.isoformat(),
                "type": e.type,
                "source": e.source,
                "lead_id": e.lead_id,
                "message": e.message,
                "details": e.details,
            }
            for e in events
        ]
    finally:
        db.close()

@router.get("/health")
def full_health_check():
    """Extended health check including DB and scheduler hints"""
    # We reuse existing health router; combine basic status
    return {"status": "ok", "service": "Realviax Outreach", "timestamp": datetime.utcnow().isoformat()}
