"""Compatibility router to match frontend API expectations."""
from fastapi import APIRouter, HTTPException, Depends, Form, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus, LandingPage
from app.services.scraper import scraper as listing_scraper
from app.services.video_service import generate_and_store_teaser, generate_and_store_full_video
from app.services.email_service import email_service
from app.core.config import settings
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/leads")
def list_leads_compat(db: Session = Depends(get_db), limit: int = 100):
    """Return leads in format expected by frontend."""
    total = db.query(Lead).count()
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return {"total": total, "leads": [l.as_dict() for l in leads]}

@router.post("/scrape")
def scrape_listing(url: str = Form(...), platform: str = Form(...)):
    """Scrape a single listing URL and create a lead."""
    try:
        data = listing_scraper.scrape(url, platform)
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    db = SessionLocal()
    try:
        # Check if lead already exists by listing_url
        existing = db.query(Lead).filter_by(listing_url=url).first()
        if existing:
            return existing.as_dict()

        lead = Lead(
            listing_url=url,
            platform=platform.lower(),
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
        db.refresh(lead)
        return lead.as_dict()
    finally:
        db.close()

@router.post("/send-email/{lead_id}")
def send_email(lead_id: int):
    """Send teaser email for a specific lead."""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not lead.teaser_video_url:
            raise HTTPException(status_code=400, detail="Lead has no teaser video")
        if not lead.agent_email:
            raise HTTPException(status_code=400, detail="Lead has no agent email")

        # Build landing page URL
        page = db.query(LandingPage).filter_by(lead_id=lead_id).first()
        if page:
            base = settings.PUBLIC_URL or settings.FRONTEND_URL or "http://localhost:8000"
            landing_url = f"{base.rstrip('/')}/p/{page.slug}"
        else:
            # Fallback to direct video URL
            if lead.teaser_video_url.startswith('/'):
                base = settings.PUBLIC_URL or settings.FRONTEND_URL or "http://localhost:8000"
                landing_url = f"{base.rstrip('/')}{lead.teaser_video_url}"
            else:
                landing_url = lead.teaser_video_url

        # Send email
        email_service.send_teaser_email(
            to_email=lead.agent_email,
            to_name=lead.agent_name or "Agent",
            lead_id=lead.id,
            landing_page_url=landing_url,
            checkout_url=None  # Could create a Stripe session if desired
        )

        # Update lead status
        lead.email_sent_at = datetime.utcnow()
        lead.status = LeadStatus.EMAIL_SENT.value
        db.commit()

        return {"status": "ok", "message": "Email sent"}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/generate/{lead_id}")
def generate_teaser(lead_id: int):
    """Generate teaser video for a lead."""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not lead.photo_urls:
            raise HTTPException(status_code=400, detail="Lead has no photos")

        video_url = generate_and_store_teaser(lead_id)
        return {"status": "ok", "video_url": video_url}
    except Exception as e:
        logger.error(f"Teaser generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/generate-full-sync/{lead_id}")
def generate_full(lead_id: int):
    """Generate full cinematic video for a lead (synchronous)."""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not lead.photo_urls:
            raise HTTPException(status_code=400, detail="Lead has no photos")

        video_url = generate_and_store_full_video(lead_id)
        return {"status": "ok", "video_url": video_url}
    except Exception as e:
        logger.error(f"Full video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/create-checkout-session/{lead_id}")
def create_checkout_session(lead_id: int):
    """Create Stripe checkout session for upsell."""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not lead.teaser_video_url:
            raise HTTPException(status_code=400, detail="Lead has no teaser video")
        if not settings.STRIPE_SECRET_KEY or not settings.FRONTEND_URL:
            raise HTTPException(status_code=500, detail="Stripe not configured")

        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Realviax Cinematic Video',
                        'description': f'60-second cinematic video for {lead.address or "property"}',
                    },
                    'unit_amount': 25000,  # $250.00 in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{settings.FRONTEND_URL}/order/success",
            cancel_url=f"{settings.FRONTEND_URL}/order/cancel",
            metadata={'lead_id': str(lead_id), 'type': 'upsell_video'}
        )

        return {
            'session_id': session.id,
            'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
        }
    except Exception as e:
        logger.error(f"Checkout session creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
