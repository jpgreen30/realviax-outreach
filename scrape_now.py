#!/usr/bin/env python3
"""Quick scraper to add fresh Zillow listing leads."""
import os, re, sys, json, logging
from datetime import datetime
sys.path.insert(0, '/home/jpgreen1/.openclaw/workspace/realviax-outreach')

from bs4 import BeautifulSoup
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus
from app.services.scraper import ListingScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

search_urls = [
    "https://www.zillow.com/homes/for_sale/New-York-NY/price-1000000-5000000/",
    "https://www.zillow.com/homes/for_sale/Los-Angeles-CA/price-1000000-5000000/",
    "https://www.zillow.com/homes/for_sale/Miami-FL/price-1000000-5000000/",
    "https://www.zillow.com/homes/for_sale/Chicago-IL/price-1000000-5000000/",
]
limit_per_source = 50

scraper = ListingScraper()
scraper._init_browser()
db = SessionLocal()
total_new = 0
try:
    for url in search_urls:
        logger.info(f"Processing search: {url}")
        page = scraper.page
        page.goto(url, timeout=60000)
        page.wait_for_selector("div[data-testid='result-list']", timeout=30000)
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if re.search(r'/homedetails/', href) and 'zpid' in href:
                full = href if href.startswith('http') else f"https://www.zillow.com{href}"
                links.append(full)
        links = list(dict.fromkeys(links))[:limit_per_source]
        logger.info(f"Found {len(links)} listing links")
        for listing_url in links:
            try:
                data = scraper._scrape_zillow(listing_url)
                exists = db.query(Lead).filter_by(listing_url=listing_url).first()
                if exists:
                    continue
                lead = Lead(
                    listing_url=listing_url,
                    platform='zillow',
                    address=data.get('address'),
                    price=data.get('price'),
                    beds=data.get('beds'),
                    baths=data.get('baths'),
                    sqft=data.get('sqft'),
                    photo_urls=data.get('photo_urls', []),
                    agent_name=data.get('agent_name'),
                    agent_email=data.get('agent_email'),
                    agent_phone=data.get('agent_phone'),
                    city=data.get('city'),
                    state=data.get('state'),
                    zip_code=data.get('zip_code'),
                    status=LeadStatus.SCRAPED.value,
                )
                db.add(lead)
                total_new += 1
                logger.info(f"Added lead: {data.get('address')} – {data.get('agent_email')}")
            except Exception as e:
                logger.warning(f"Failed to scrape listing {listing_url}: {e}")
        db.commit()
finally:
    scraper._close_browser()
    db.close()

print(f"Total new leads added: {total_new}")
