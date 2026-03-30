"""Video service with Supabase storage integration and quality/style options"""
from app.services.video_generator import video_gen
from app.services.supabase_video_service import supabase_video_service
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus
import logging

logger = logging.getLogger(__name__)

def generate_and_store_teaser(lead_id: int, style_options: dict = None) -> str:
    """Generate teaser video for a lead and upload to Supabase"""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        if not lead.photo_urls:
            raise ValueError(f"Lead {lead_id} has no photos")
        
        # Generate video locally
        video_path = video_gen.generate_teaser(lead_id, lead.photo_urls, {
            "address": lead.address,
            "price": lead.price,
            "beds": lead.beds,
            "baths": lead.baths,
            "sqft": lead.sqft,
            "tagline": "Luxury living at its finest"
        }, **(style_options or {}))
        
        # Upload to Supabase
        public_url = supabase_video_service.upload_video(video_path, lead_id, "teaser")
        
        # Update lead with video URL
        lead.teaser_video_url = public_url
        db.commit()
        
        logger.info(f"Generated and stored teaser for lead {lead_id}: {public_url}")
        return public_url
    finally:
        db.close()

def generate_videos_batch(limit: int = 50, style_options: dict = None) -> int:
    """Generate teaser videos for all pending leads"""
    db = SessionLocal()
    try:
        leads = db.query(Lead).filter(
            Lead.teaser_video_url == None
        ).limit(limit).all()
        count = 0
        for lead in leads:
            try:
                video_path = video_gen.generate_teaser(lead.id, lead.photo_urls, {
                    "address": lead.address,
                    "price": lead.price,
                    "beds": lead.beds,
                    "baths": lead.baths,
                    "sqft": lead.sqft,
                }, **(style_options or {}))
                public_url = supabase_video_service.upload_video(video_path, lead.id, "teaser")
                lead.teaser_video_url = public_url
                db.commit()
                count += 1
                logger.info(f"Generated teaser for lead {lead.id}")
            except Exception as e:
                logger.error(f"Teaser generation failed for lead {lead.id}: {e}")
                db.rollback()
        return count
    finally:
        db.close()

def generate_and_store_full_video(lead_id: int, style_options: dict = None) -> str:
    """Generate full cinematic video for a lead after payment"""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
        if not lead.photo_urls:
            raise ValueError(f"Lead {lead_id} has no photos")
        
        # Generate full video
        video_path = video_gen.generate_full(lead.id, lead.photo_urls, {
            "address": lead.address,
            "price": lead.price,
            "beds": lead.beds,
            "baths": lead.baths,
            "sqft": lead.sqft,
            "tagline": "Cinematic property tour"
        }, **(style_options or {}))
        
        # Upload to Supabase
        public_url = supabase_video_service.upload_video(video_path, lead.id, "full")
        
        # Update lead
        lead.full_video_url = public_url
        db.commit()
        
        logger.info(f"Generated and stored full video for lead {lead_id}: {public_url}")
        return public_url
    finally:
        db.close()
