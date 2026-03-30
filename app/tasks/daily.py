"""
Daily automated pipeline tasks.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.utils.db import SessionLocal
from app.models.models import Lead
from app.services.scraper import run_scrape_for_all_sources
from app.services.email_service import send_outreach_emails
from app.services.video_generator import generate_teaser_for_leads
from app.core.supabase import get_supabase

logger = logging.getLogger("realviax.tasks")

def run_daily_pipeline():
    """Scheduled job: runs once per day."""
    logger.info("Starting daily pipeline")
    try:
        # 1. Scrape new listings
        run_scrape_for_all_sources()
        logger.info("Scraping completed")
        # 2. Generate teaser videos for new scraped leads without teaser
        db = SessionLocal()
        try:
            count = generate_teaser_for_leads(db, limit=50)
            logger.info(f"Generated teaser videos for {count} leads")
        finally:
            db.close()
        # 3. Send outreach emails to leads with teaser and no email_sent
        sent = send_outreach_emails()
        logger.info(f"Sent {sent} outreach emails")
        # 4. Update analytics (placeholder)
        # ...
        logger.info("Daily pipeline completed successfully")
    except Exception as e:
        logger.exception(f"Daily pipeline failed: {e}")
