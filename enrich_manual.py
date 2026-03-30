"""Manual enrichment using Playwright: visit each lead and extract any visible contact (phone优先)"""
import os
import json
import re
import logging
import time
from playwright.sync_api import sync_playwright
from app.utils.db import SessionLocal
from app.models.models import Lead

logger = logging.getLogger(__name__)

def extract_contact(html: str) -> tuple:
    """Extract phone and email from page HTML."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for phone numbers
    phone = None
    phone_pattern = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    text = soup.get_text()
    phones = re.findall(phone_pattern, text)
    # Filter to likely phone numbers (10 digits)
    for p in phones:
        digits = re.sub(r'\D', '', p)
        if len(digits) == 10:
            phone = p
            break
    
    # Look for email
    email = None
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, text)
    if emails:
        # Prefer non-noreply emails
        for e in emails:
            if 'noreply' not in e.lower() and 'zillow' not in e.lower() and 'redfin' not in e.lower():
                email = e
                break
        if not email:
            email = emails[0]
    
    # Also check mailto links
    if not email:
        mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
        if mailto:
            m = re.search(email_pattern, mailto['href'])
            if m:
                email = m.group(0)
    
    return phone, email

def enrich_leads_manual(lead_ids: list):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()
    
    # Optional: login to Zillow to unlock contact info
    cred_path = os.path.expanduser("~/.openclaw/credentials/web-credentials.json")
    if os.path.exists(cred_path):
        with open(cred_path, 'r') as f:
            cred_data = json.load(f)
        zillow = cred_data.get('sites', {}).get('zillow')
        if zillow:
            page.goto("https://www.zillow.com/user/login.htm", timeout=30000)
            time.sleep(2)
            page.fill('input[name="username"]', zillow['username'])
            page.fill('input[name="password"]', zillow['password'])
            page.click('button[type="submit"]')
            time.sleep(5)
            logger.info("Logged into Zillow")
    
    db = SessionLocal()
    try:
        for lead_id in lead_ids:
            lead = db.query(Lead).get(lead_id)
            if not lead:
                continue
            if lead.agent_email or lead.agent_phone:
                logger.info(f"Lead {lead_id} already has contact")
                continue
            try:
                logger.info(f"Visiting: {lead.listing_url}")
                page.goto(lead.listing_url, timeout=60000)
                time.sleep(3)
                html = page.content()
                phone, email = extract_contact(html)
                updated = False
                if phone:
                    lead.agent_phone = phone
                    updated = True
                if email:
                    lead.agent_email = email
                    updated = True
                if updated:
                    db.commit()
                    logger.info(f"Lead {lead_id} updated: phone={phone}, email={email}")
                else:
                    logger.warning(f"No contact found for lead {lead_id}")
            except Exception as e:
                logger.error(f"Error on lead {lead_id}: {e}")
                db.rollback()
    finally:
        db.close()
        page.close()
        context.close()
        browser.close()
        p.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    # Get leads without email and with photo URLs
    leads = db.query(Lead).filter(Lead.agent_email == None, Lead.photo_urls != None).limit(5).all()
    lead_ids = [l.id for l in leads]
    db.close()
    logger.info(f"Enriching {len(lead_ids)} leads")
    enrich_leads_manual(lead_ids)