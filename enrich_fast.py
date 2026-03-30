"""Enrich leads with agent phone/email by visiting pages and clicking contact buttons (no login)"""
import os
import json
import re
import logging
import time
from playwright.sync_api import sync_playwright
from app.utils.db import SessionLocal
from app.models.models import Lead
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_contact_fast(html: str) -> tuple:
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    phone = None
    email = None

    # Find first 10-digit phone
    phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if phone_match:
        phone = phone_match.group()

    # Find email (avoid generic)
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    for e in emails:
        if not any(x in e.lower() for x in ['noreply', 'zillow', 'redfin', 'support', 'info@']):
            email = e
            break
    if not email and emails:
        email = emails[0]

    # Check mailto links
    if not email:
        mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
        if mailto:
            m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
            if m:
                email = m.group(0)

    return phone, email

def enrich_leads_fast(lead_ids: list):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()

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
                logger.info(f"Loading: {lead.listing_url}")
                page.goto(lead.listing_url, timeout=60000)
                time.sleep(3)

                # Try to click any contact-related button
                contact_selectors = [
                    "button:has-text('Call')",
                    "button:has-text('Contact')",
                    "button:has-text('Show')",
                    "a:has-text('Contact')",
                    "button[class*='contact']",
                    "button[data-test*='contact']",
                    "button[class*='agent']",
                ]
                for sel in contact_selectors:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible():
                            btn.click()
                            time.sleep(2)
                            logger.info(f"Clicked selector: {sel}")
                            break
                    except:
                        pass

                html = page.content()
                phone, email = extract_contact_fast(html)
                if phone or email:
                    if phone:
                        lead.agent_phone = phone
                    if email:
                        lead.agent_email = email
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
    # Prioritize leads with photos and price > 500k
    leads = db.query(Lead).filter(
        Lead.photo_urls != None,
        Lead.agent_email == None,
        Lead.price > 500000
    ).limit(5).all()
    lead_ids = [l.id for l in leads]
    db.close()
    logger.info(f"Enriching {len(lead_ids)} leads")
    enrich_leads_fast(lead_ids)