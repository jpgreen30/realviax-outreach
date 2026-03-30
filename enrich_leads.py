"""Enrich leads with agent contact info using Playwright (Zillow login)"""
import os
import json
import logging
import time
from typing import List
from playwright.sync_api import sync_playwright
from app.core.config import settings
from app.utils.db import SessionLocal
from app.models.models import Lead
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

CRED_PATH = os.path.expanduser("~/.openclaw/credentials/web-credentials.json")
COOKIES_FILE = os.path.join(settings.VIDEO_OUTPUT_DIR, "..", ".zillow_cookies.json")

def load_credentials():
    with open(CRED_PATH, 'r') as f:
        data = json.load(f)
    return data.get('sites', {}).get('zillow')

def login_zillow(page, username, password):
    page.goto("https://www.zillow.com/user/login.htm", timeout=30000)
    time.sleep(2)
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    time.sleep(5)
    # Save cookies
    cookies = page.context.cookies()
    os.makedirs(os.path.dirname(COOKIES_FILE), exist_ok=True)
    with open(COOKIES_FILE, 'w') as f:
        json.dump(cookies, f)
    logger.info("Logged in and saved cookies")

def ensure_logged_in(page):
    # Try loading cookies if exist
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        page.context.add_cookies(cookies)
    # Verify by checking account page
    page.goto("https://www.zillow.com/my/", timeout=30000)
    time.sleep(2)
    if "login" in page.url.lower():
        # Need to login
        creds = load_credentials()
        if creds:
            login_zillow(page, creds['username'], creds['password'])
        else:
            logger.error("No credentials for Zillow login")
    else:
        logger.info("Already logged in")

def extract_agent_info_from_page(html: str) -> tuple:
    soup = BeautifulSoup(html, 'html.parser')
    agent_name = agent_email = agent_phone = None

    # Look for agent div
    agent_div = soup.find("div", class_=re.compile(r"agent", re.I))
    if agent_div:
        name_el = agent_div.find(["span", "p", "h3", "h4"], class_=re.compile(r"name", re.I))
        if name_el:
            agent_name = name_el.get_text(strip=True)
        phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", agent_div.get_text())
        if phone_match:
            agent_phone = phone_match.group()
        email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", agent_div.get_text())
        if email_match:
            agent_email = email_match.group()

    # Try mailto
    if not agent_email:
        mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
        if mailto:
            email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
            if email_match:
                agent_email = email_match.group(0)

    return agent_name, agent_email, agent_phone

def enrich_leads(lead_ids: List[int]):
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()
    ensure_logged_in(page)

    db = SessionLocal()
    try:
        for lead_id in lead_ids:
            lead = db.query(Lead).get(lead_id)
            if not lead:
                logger.warning(f"Lead {lead_id} not found")
                continue
            if lead.agent_email:
                logger.info(f"Lead {lead_id} already has email: {lead.agent_email}")
                continue
            try:
                logger.info(f"Visiting lead {lead_id}: {lead.listing_url}")
                page.goto(lead.listing_url, timeout=60000)
                time.sleep(3)
                
                # Attempt to click "Show contact info" or similar
                contact_selectors = [
                    "button:has-text('Show contact')",
                    "a:has-text('Show contact')",
                    "button:has-text('Contact agent')",
                    "a:has-text('Contact agent')",
                    "button[data-test='contact-agent']",
                    "button[class*='contact']",
                ]
                clicked = False
                for selector in contact_selectors:
                    try:
                        btn = page.locator(selector).first
                        if btn.is_visible():
                            btn.click()
                            clicked = True
                            time.sleep(2)
                            logger.info(f"Clicked contact button with selector: {selector}")
                            break
                    except:
                        continue
                
                html = page.content()
                name, email, phone = extract_agent_info_from_page(html)
                if email:
                    lead.agent_name = name or lead.agent_name
                    lead.agent_email = email
                    lead.agent_phone = phone or lead.agent_phone
                    db.commit()
                    logger.info(f"Lead {lead_id} enriched: {email}")
                else:
                    logger.warning(f"No email found for lead {lead_id}")
            except Exception as e:
                logger.error(f"Error enriching lead {lead_id}: {e}")
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
    # Get all leads without email
    leads = db.query(Lead).filter(Lead.agent_email == None).limit(8).all()
    lead_ids = [l.id for l in leads]
    db.close()
    logger.info(f"Enriching {len(lead_ids)} leads")
    enrich_leads(lead_ids)
