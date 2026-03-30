"""Batch scrape Redfin listings and populate leads with contact info"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.redfin_scraper import redfin_scraper
from app.utils.db import SessionLocal
from app.models.models import Lead
from app.services.video_service import generate_videos_batch
from app.services.email_service import send_outreach_emails
import logging

logging.basicConfig(level=logging.INFO)

search_urls = [
    "https://www.redfin.com/city/16951/CA/Beverly-Hills",
    "https://www.redfin.com/city/16958/CA/Los-Angeles",
    "https://www.redfin.com/city/16960/CA/San-Francisco",
    "https://www.redfin.com/state/16959/NY/New-York",
    "https://www.redfin.com/city/16993/FL/Miami",
]

db = SessionLocal()
total_new = 0
for search_url in search_urls:
    try:
        urls = redfin_scraper.fetch_listing_urls(search_url, limit=5)
        for url in urls:
            if db.query(Lead).filter_by(listing_url=url).first():
                continue
            try:
                data = redfin_scraper.scrape(url)
                lead = Lead(**data)
                db.add(lead)
                db.commit()
                total_new += 1
                logging.info(f"Added lead {lead.id} | agent_email={data.get('agent_email')} | price={data.get('price')}")
            except Exception as e:
                logging.error(f"Failed to scrape {url}: {e}")
                db.rollback()
    except Exception as e:
        logging.error(f"Error processing search {search_url}: {e}")
db.close()
print(f"Total new Redfin leads: {total_new}")

# Generate teasers for new leads without videos
print("Generating teaser videos...")
from app.services.video_service import generate_videos_batch
generated = generate_videos_batch(limit=50)
print(f"Generated {generated} teaser videos")

# Send outreach emails
print("Sending outreach emails...")
from app.services.email_service import send_outreach_emails
sent = send_outreach_emails(limit=200)
print(f"Sent {sent} emails")
