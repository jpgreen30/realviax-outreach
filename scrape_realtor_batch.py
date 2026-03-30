"""Batch scrape Realtor.com listings and populate leads"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.realtor_scraper import realtor_scraper
from app.utils.db import SessionLocal
from app.models.models import Lead
import logging

logging.basicConfig(level=logging.INFO)

# Define target searches (high-value markets)
search_urls = [
    "https://www.realtor.com/realestateandhomes-search/Beverly-Hills_CA",
    "https://www.realtor.com/realestateandhomes-search/Los-Angeles_CA",
    "https://www.realtor.com/realestateandhomes-search/San-Francisco_CA",
    "https://www.realtor.com/realestateandhomes-search/New-York_NY",
    "https://www.realtor.com/realestateandhomes-search/Miami_FL",
]

db = SessionLocal()
total_new = 0
for search_url in search_urls:
    try:
        urls = realtor_scraper.fetch_listing_urls(search_url, limit=5)
        for url in urls:
            if db.query(Lead).filter_by(listing_url=url).first():
                continue
            try:
                data = realtor_scraper.scrape(url)
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
print(f"Total new Realtor.com leads: {total_new}")
