"""Leads management router"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus
from app.services.scraper import scraper
from app.services.video_service import generate_and_store_teaser
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def list_leads(db: Session = Depends(get_db), limit: int = 100, offset: int = 0):
    total = db.query(Lead).count()
    leads = db.query(Lead).order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "leads": [l.as_dict() for l in leads]}

@router.get("/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter_by(id=lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.as_dict()

@router.post("/scrape")
def trigger_scrape(limit_per_source: int = 50):
    """Trigger manual scrape (for admin)"""
    from app.services.scraper import run_scrape_for_all_sources
    try:
        count = run_scrape_for_all_sources()
        return {"status": "ok", "scraped": count}
    except Exception as e:
        logger.error(f"Manual scrape failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/generate-video")
def generate_video(lead_id: int, db: Session = Depends(get_db)):
    """Generate teaser video for a specific lead"""
    lead = db.query(Lead).filter_by(id=lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.photo_urls:
        raise HTTPException(status_code=400, detail="Lead has no photos")
    try:
        url = generate_and_store_teaser(lead_id)
        return {"status": "ok", "video_url": url}
    except Exception as e:
        logger.error(f"Video generation failed for lead {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/stats")
def stats(db: Session = Depends(get_db)):
    stats = {
        "total": db.query(Lead).count(),
        "scraped": db.query(Lead).filter_by(status=LeadStatus.SCRAPED).count(),
        "video_ready": db.query(Lead).filter_by(status=LeadStatus.VIDEO_READY).count(),
        "email_sent": db.query(Lead).filter_by(status=LeadStatus.EMAIL_SENT).count(),
        "emails_sent_today": 0,  # TODO: implement
    }
    return stats
