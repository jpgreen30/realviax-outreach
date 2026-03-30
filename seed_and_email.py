#!/usr/bin/env python3
import sys, os, json, logging
sys.path.insert(0, '/home/jpgreen1/.openclaw/workspace/realviax-outreach')
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus
from app.services.scraper import ListingScraper
from app.services.video_service import generate_and_store_teaser
from app.services.email_service import create_stripe_checkout_session
from app.core.config import settings
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load seed URLs
with open('seed_urls.json') as f:
    urls = json.load(f)

scraper = ListingScraper()
scraper._init_browser()
db = SessionLocal()
try:
    for url in urls:
        # Check if already exists
        if db.query(Lead).filter_by(listing_url=url).first():
            logger.info(f"Lead exists: {url}")
            continue
        # Scrape data
        try:
            data = scraper._scrape_zillow(url)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            continue
        # Create lead
        lead = Lead(
            listing_url=url,
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
        db.commit()
        logger.info(f"Added lead: {lead.id} – {lead.agent_email}")
        # Generate teaser video
        try:
            teaser_path = generate_and_store_teaser(lead.id, force=True)
            lead.teaser_video_url = teaser_path
            db.commit()
            logger.info(f"Teaser video generated for lead {lead.id}: {teaser_path}")
        except Exception as e:
            logger.error(f"Teaser generation failed for lead {lead.id}: {e}")
            continue
        # Send teaser email with $149 offer
        try:
            checkout_url = create_stripe_checkout_session(lead.id, amount_override=149)
            video_url = f"{settings.PUBLIC_URL.rstrip('/')}{lead.teaser_video_url}" if lead.teaser_video_url.startswith('/') else lead.teaser_video_url
            html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:system-ui, sans-serif; background:#f7f7f7; padding:20px;">
  <div style="max-width:600px; margin:0 auto; background:#fff; padding:20px; border-radius:8px;">
    <h2 style="color:#1a1a2e;">Your Listing Teaser + Special Offer</h2>
    <p>Hello {lead.agent_name or "Agent"},</p>
    <p>We've created a 30-second teaser video for your listing at {lead.address}.</p>
    <p>For a limited time, upgrade to the full 60-second cinematic version for <strong>$149</strong> (regular $250).</p>
    <p>Watch the teaser:</p>
    <p style="text-align:center; margin:20px 0;">
      <a href="{video_url}" style="background:#1a1a2e; color:#fff; padding:12px 24px; text-decoration:none; border-radius:4px;">View Teaser</a>
    </p>
    <p style="text-align:center; margin:20px 0;">
      <a href="{checkout_url}" style="background:#10b981; color:#fff; padding:12px 24px; text-decoration:none; border-radius:4px; font-weight:bold;">Upgrade for $149</a>
    </p>
    <p><em>Offer valid 24 hours.</em></p>
    <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
    <p style="color:#888; font-size:12px;">Sent by RealviaX</p>
  </div>
</body>
</html>"""
            payload = {
                "sender": {"email": settings.BREVO_SENDER_EMAIL, "name": settings.BREVO_SENDER_NAME},
                "to": [{"email": lead.agent_email, "name": lead.agent_name}],
                "subject": "Your Teaser Video + Special Upgrade Offer",
                "htmlContent": html,
            }
            headers = {"api-key": settings.BREVO_API_KEY, "content-type": "application/json", "accept": "application/json"}
            resp = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=15)
            if resp.status_code >= 200 and resp.status_code < 300:
                logger.info(f"Sent email to {lead.agent_email}")
            else:
                logger.error(f"Email failed {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Email send error: {e}")
finally:
    scraper._close_browser()
    db.close()

logger.info("Seeding complete.")
