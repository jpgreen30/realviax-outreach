#!/usr/bin/env python3
"""
Realviax Outreach Automation - Main Orchestrator

Workflow:
1. Scrape listings from configured platforms
2. Extract agent contact info and listing details
3. Generate 30-second teaser video
4. Send personalized email with video embedded
5. (Optional) Send SMS follow-up
6. Track opens/clicks/conversions
"""
import os
import sys
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import multiprocessing as mp

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import Settings
from scraper import get_scraper
from video.generator import VideoGenerator
from outreach.emailer import BrevoEmailer, EmailRenderer
from outreach.texter import TwilioTexter
from outreach.tracker import Tracker
from database.models import LeadStatus, Platform

# Setup logging
logging.basicConfig(
    level=getattr(logging, Settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/realviax_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealviaxOrchestrator:
    def __init__(self):
        self.settings = Settings()
        self.tracker = Tracker()
        
        # Initialize video generator
        self.video_gen = VideoGenerator(
            logo_path=self.settings.LOGO_PATH,
            music_dir=self.settings.MUSIC_DIR,
            output_dir=self.settings.VIDEO_OUTPUT_DIR,
            template_teaser=self.settings.VIDEO_TEMPLATE_TEASER,
            template_full=self.settings.VIDEO_TEMPLATE_FULL
        )
        
        # Initialize email
        if self.settings.BREVO_API_KEY:
            self.emailer = BrevoEmailer(
                api_key=self.settings.BREVO_API_KEY,
                sender_email=self.settings.BREVO_SENDER_EMAIL,
                sender_name=self.settings.BREVO_SENDER_NAME
            )
        else:
            self.emailer = None
            logger.warning("Brevo API key not set. Email sending disabled.")
        
        # Initialize SMS
        if self.settings.TWILIO_ACCOUNT_SID:
            self.texter = TwilioTexter(
                account_sid=self.settings.TWILIO_ACCOUNT_SID,
                auth_token=self.settings.TWILIO_AUTH_TOKEN,
                from_number=self.settings.TWILIO_FROM_NUMBER
            )
        else:
            self.texter = None
            logger.warning("Twilio credentials not set. SMS sending disabled.")
        
        # Load email templates
        self.email_templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Load email templates from files or defaults"""
        templates = {}
        # In production, load from actual template files
        # For now, use inline rendering from EmailRenderer
        return {
            "teaser": "inline",
            "upsell": "inline"
        }
    
    async def process_listing(self, url: str, platform: str) -> Dict[str, Any]:
        """Full pipeline: scrape -> video -> email -> track"""
        logger.info(f"Processing listing: {url} ({platform})")
        
        # 1. Scrape
        scraper = get_scraper(platform)
        listing_data = scraper.scrape_listing(url)
        if not listing_data:
            logger.error(f"Failed to scrape {url}")
            return {"success": False, "error": "Scraping failed"}
        
        # 2. Generate teaser video
        try:
            video_path = self.video_gen.generate_teaser(
                listing_data=listing_data,
                photo_urls=listing_data.get("photo_urls", [])
            )
            video_size = os.path.getsize(video_path)
            logger.info(f"Teaser video created: {video_path}")
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {"success": False, "error": f"Video failed: {e}"}
        
        # 3. Track video
        video = self.tracker.log_video_generated(
            listing_url=url,
            video_type="teaser",
            file_path=video_path,
            file_size=video_size,
            duration=30
        )
        
        # 4. Send email if we have agent email
        agent_email = listing_data.get("agent_email")
        agent_name = listing_data.get("agent_name", "Agent")
        
        if agent_email and self.emailer:
            # Render email
            html = EmailRenderer.render_teaser_email(
                agent_name=agent_name,
                listing_address=listing_data.get("address", "the property"),
                video_url=video_path,  # TODO: upload to CDN and get public URL
                listing_data=listing_data,
                unsubscribe_link=f"https://realviax.com/unsubscribe?email={agent_email}"
            )
            
            # Send
            result = self.emailer.send_email(
                to_email=agent_email,
                to_name=agent_name,
                subject=f"Free cinematic video for your listing at {listing_data.get('address', 'property')}",
                html_content=html
            )
            
            if result["success"]:
                self.tracker.log_email_sent(
                    listing_url=url,
                    to_email=agent_email,
                    message_id=result["message_id"],
                    template="teaser",
                    agent_name=agent_name
                )
                logger.info(f"Email sent to {agent_email}")
            else:
                logger.error(f"Email failed: {result.get('error')}")
        
        # 5. Optional: send SMS if phone available
        agent_phone = listing_data.get("agent_phone")
        if agent_phone and self.texter:
            sms_result = self.texter.send_teaser_sms(
                to_name=agent_name,
                to_number=agent_phone,
                video_url=video_path,  # Would need CDN URL
                listing_address=listing_data.get("address", "your listing"),
                price=str(listing_data.get("price", ""))
            )
            if sms_result["success"]:
                logger.info(f"SMS sent to {agent_phone}")
        
        return {
            "success": True,
            "listing_url": url,
            "video_path": video_path,
            "agent_email": agent_email,
            "agent_phone": agent_phone
        }
    
    async def process_batch(self, urls: List[str], platform: str, max_concurrent: int = 5):
        """Process multiple listings concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def worker(url):
            async with semaphore:
                return await self.process_listing(url, platform)
        
        tasks = [worker(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        logger.info(f"Batch complete: {successful}/{len(urls)} processed successfully")
        return results

def load_credentials():
    """Load API keys from environment or config file"""
    # Check for env vars
    if not os.getenv("BREVO_API_KEY"):
        logger.warning("BREVO_API_KEY not set in environment")
    if not os.getenv("TWILIO_ACCOUNT_SID"):
        logger.warning("TWILIO_ACCOUNT_SID not set in environment")
    
    # Could also load from a credentials file
    cred_file = "config/credentials.json"
    if os.path.exists(cred_file):
        with open(cred_file) as f:
            creds = json.load(f)
            os.environ.update(creds)

def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Realviax Outreach Automation")
    parser.add_argument("--url", help="Single listing URL to process")
    parser.add_argument("--platform", choices=["zillow", "redfin", "realtor_com"], 
                       required="--url" in sys.argv)
    parser.add_argument("--batch", help="File with list of URLs, one per line")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max parallel workers")
    parser.add_argument("--dashboard", action="store_true", help="Start web dashboard")
    
    args = parser.parse_args()
    
    if args.dashboard:
        # Start FastAPI dashboard
        logger.info("Starting dashboard on port 8000...")
        # TODO: Implement dashboard launch
        return
    
    load_credentials()
    
    orchestrator = RealviaxOrchestrator()
    
    if args.url:
        # Single URL
        result = asyncio.run(orchestrator.process_listing(args.url, args.platform))
        print(json.dumps(result, indent=2, default=str))
    
    elif args.batch:
        # Batch processing
        with open(args.batch) as f:
            urls = [line.strip() for line in f if line.strip()]
        results = asyncio.run(orchestrator.process_batch(urls, args.platform, args.max_concurrent))
        # Output summary
        success = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        print(f"Processed {len(urls)} URLs: {success} successful")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    mp.freeze_support()
    main()