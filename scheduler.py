"""Cron scheduler for Realviax Outreach"""
import os
import time
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.scraper import run_scrape_for_all_sources
from app.services.video_service import generate_videos_batch
from app.services.email_service import send_outreach_emails
from app.utils.db import SessionLocal
from app.models.models import LeadStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealviaxScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        # Scrape new listings daily at 6 AM UTC
        self.scheduler.add_job(
            self.run_scrape_job,
            trigger=CronTrigger(hour=6, minute=0),
            id='scrape_job',
            name='Scrape new listings daily',
            replace_existing=True
        )
        
        # Generate videos every 2 hours
        self.scheduler.add_job(
            self.run_video_job,
            trigger=CronTrigger(hour='*/2', minute=15),
            id='video_job',
            name='Generate teaser videos',
            replace_existing=True
        )
        
        # Send emails every 3 hours
        self.scheduler.add_job(
            self.run_email_job,
            trigger=CronTrigger(hour='*/3', minute=30),
            id='email_job',
            name='Send outreach emails',
            replace_existing=True
        )
        
        # Full pipeline run on startup (after 1 minute)
        self.scheduler.add_job(
            self.run_full_pipeline,
            trigger='date',
            run_date=datetime.now().replace(second=0, microsecond=0),
            id='full_pipeline_startup',
            name='Full pipeline run on startup'
        )
    
    def run_scrape_job(self):
        logger.info("Starting scrape job...")
        try:
            count = run_scrape_for_all_sources()
            logger.info(f"Scrape job completed: {count} new leads scraped")
        except Exception as e:
            logger.error(f"Scrape job failed: {e}", exc_info=True)
    
    def run_video_job(self, limit=100):
        logger.info("Starting video generation job...")
        try:
            count = generate_videos_batch(limit=limit)
            logger.info(f"Video job completed: {count} videos generated")
        except Exception as e:
            logger.error(f"Video job failed: {e}", exc_info=True)
    
    def run_email_job(self, limit=200):
        logger.info("Starting email outreach job...")
        try:
            sent = send_outreach_emails(limit=limit)
            logger.info(f"Email job completed: {sent} emails sent")
        except Exception as e:
            logger.error(f"Email job failed: {e}", exc_info=True)
    
    def run_full_pipeline(self):
        """Run the full pipeline: scrape -> generate videos -> send emails"""
        logger.info("Starting full pipeline run...")
        try:
            # Step 1: Scrape
            scraped = run_scrape_for_all_sources()
            logger.info(f"Full pipeline scrape: {scraped} new leads")
            
            # Step 2: Generate videos
            videos = generate_videos_batch(limit=100)
            logger.info(f"Full pipeline videos: {videos} generated")
            
            # Step 3: Send emails
            emails = send_outreach_emails(limit=200)
            logger.info(f"Full pipeline emails: {emails} sent")
            
            logger.info("Full pipeline run completed successfully")
        except Exception as e:
            logger.error(f"Full pipeline failed: {e}", exc_info=True)
    
    def start(self):
        logger.info("Starting Realviax Scheduler...")
        self.scheduler.start()
        logger.info("Scheduler started. Jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.name}: {job.trigger}")
    
    def shutdown(self):
        logger.info("Shutting down scheduler...")
        self.scheduler.shutdown()
        logger.info("Scheduler shut down")

if __name__ == "__main__":
    scheduler = RealviaxScheduler()
    scheduler.start()
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
