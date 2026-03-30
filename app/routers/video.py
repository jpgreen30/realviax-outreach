"""Video generation router"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from app.utils.db import SessionLocal
from app.models.models import Lead
from app.services.video_service import generate_videos_batch
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/batch-generate")
def batch_generate(limit: int = 100):
    """Generate teaser videos for pending leads"""
    try:
        count = generate_videos_batch(limit=limit)
        return {"status": "ok", "generated": count}
    except Exception as e:
        logger.error(f"Batch video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lead_id}/status")
def video_status(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter_by(id=lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {
        "lead_id": lead_id,
        "has_video": bool(lead.teaser_video_url),
        "video_url": lead.teaser_video_url
    }
