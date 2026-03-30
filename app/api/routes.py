from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import stripe
from pathlib import Path

from app.core.config import settings
from app.models.models import Lead, LeadStatus
from app.schemas.schemas import (
    LeadCreate, LeadResponse, LeadUpdate, Metrics,
    ScrapeRequest, ScrapeResponse, MessageResponse, VideoGenerateResponse
)
from app.services import scraper, video_gen, email_service, sms_service
from app.utils.db import get_db

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()

@router.get("/leads", response_model=List[LeadResponse])
def get_leads(limit: int = 20, db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(limit).all()
    return leads

@router.post("/scrape", response_model=ScrapeResponse)
def scrape_listing(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    url: str = Form(...),
    platform: str = Form(...)
):
    try:
        data = scraper.scrape(url, platform)
    except Exception as e:
        raise HTTPException(500, f"Scraping failed: {str(e)}")

    lead = Lead(**data)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    background_tasks.add_task(generate_and_store_video, lead.id, data)

    return {"success": True, "lead": lead}

@router.post("/generate/{lead_id}", response_model=VideoGenerateResponse)
def generate_video(lead_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    background_tasks.add_task(generate_and_store_video, lead.id, {
        "photo_urls": lead.photo_urls,
        "address": lead.address,
        "price": lead.price,
    })
    return {"success": True, "message": "Video generation started"}

@router.post("/send-email/{lead_id}", response_model=MessageResponse)
def send_email(lead_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.agent_email:
        raise HTTPException(400, "No agent email on lead")
    background_tasks.add_task(send_teaser_email_task, lead_id)
    return {"success": True, "message": "Email queued"}

@router.get("/metrics", response_model=Metrics)
def get_metrics(db: Session = Depends(get_db)):
    total_leads = db.query(Lead).count()
    emails_sent = db.query(Lead).filter(Lead.email_sent_at.isnot(None)).count()
    conversions = db.query(Lead).filter(Lead.converted_at.isnot(None)).count()
    revenue = conversions * 250.0
    return Metrics(total_leads=total_leads, emails_sent=emails_sent, conversions=conversions, revenue=revenue)

# Payments: Create Checkout Session for full video upsell
@router.post("/create-checkout-session/{lead_id}")
def create_checkout_session(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.full_video_url:
        raise HTTPException(400, "Full video not ready")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Full Cinematic Video',
                        'description': f'60-second cinematic video for {lead.address}',
                    },
                    'unit_amount': 25000,  # $250.00 in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{settings.FRONTEND_URL}/dashboard/outreach?payment=success&lead_id={lead_id}",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard/outreach?payment=cancel&lead_id={lead_id}",
            metadata={"lead_id": lead_id},
            client_reference_id=str(lead_id),
        )
        return {"session_id": session.id, "publishable_key": settings.STRIPE_PUBLISHABLE_KEY}
    except Exception as e:
        raise HTTPException(500, str(e))

# Stripe webhook endpoint
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(400, f"Webhook signature verification failed: {e}")

    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        lead_id = session.get("metadata", {}).get("lead_id")
        if lead_id:
            lead = db.query(Lead).get(int(lead_id))
            if lead:
                lead.payment_received = True
                lead.converted_to_full_video = True
                lead.converted_at = datetime.utcnow()
                lead.status = LeadStatus.CONVERTED.value
                db.commit()
    return {"status": "ok"}

# Brevo webhook endpoint
@router.post("/webhooks/brevo")
async def brevo_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("X-Brevo-Webhook-Signature") or request.headers.get("X-Brevo-Signature")
    # Optional: verify signature using settings.BREVO_WEBHOOK_SECRET
    try:
        event = await request.json()
    except:
        raise HTTPException(400, "Invalid JSON")

    event_type = event.get("event")
    message_id = event.get("message", {}).get("messageId")
    # Brevo includes custom params in `params` key
    params = event.get("params", {})
    lead_id = params.get("lead_id")
    if not lead_id:
        # Could also map by email if needed
        return {"status": "ignored"}

    lead = db.query(Lead).get(int(lead_id))
    if not lead:
        return {"status": "lead not found"}

    # Update lead based on event
    now = datetime.utcnow()
    if event_type == "sent":
        lead.email_sent_at = now
        lead.status = LeadStatus.EMAIL_SENT.value
    elif event_type == "delivered":
        lead.email_sent_at = lead.email_sent_at or now
    elif event_type == "opened":
        lead.email_opened = True
        lead.email_opened_at = now
        lead.status = LeadStatus.EMAIL_OPENED.value
    elif event_type == "clicked":
        lead.email_clicked = True
        lead.email_clicked_at = now
        lead.status = LeadStatus.EMAIL_CLICKED.value
    elif event_type == "bounce":
        lead.status = LeadStatus.BOUNCED.value
    db.commit()
    return {"status": "ok"}

@router.post("/test-lead", response_model=ScrapeResponse)
def create_test_lead(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Create a sample lead with real estate photos for demo purposes"""
    sample_data = {
        "listing_url": "https://example.com/test-listing",
        "platform": "zillow",
        "address": "123 Luxury Lane, Beverly Hills, CA 90210",
        "price": 2500000,
        "beds": 5,
        "baths": 4,
        "sqft": 4500,
        "property_type": "Single Family",
        "city": "Beverly Hills",
        "state": "CA",
        "zip_code": "90210",
    "photo_urls": [
        "https://picsum.photos/1080/1080?random=1",
        "https://picsum.photos/1080/1080?random=2",
        "https://picsum.photos/1080/1080?random=3",
        "https://picsum.photos/1080/1080?random=4",
        "https://picsum.photos/1080/1080?random=5",
        "https://picsum.photos/1080/1080?random=6",
        "https://picsum.photos/1080/1080?random=7",
        "https://picsum.photos/1080/1080?random=8",
    ],
        "agent_name": "Sarah Johnson",
        "agent_email": "sarah@example.com",
        "agent_phone": "+13105551234",
        "office_name": "Luxury Estates"
    }
    lead = Lead(**sample_data)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Generate teaser video in background
    background_tasks.add_task(generate_and_store_video, lead.id, sample_data)

    return {"success": True, "lead": lead}

@router.post("/generate-full/{lead_id}", response_model=VideoGenerateResponse)
def generate_full_video(lead_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    background_tasks.add_task(generate_full_task, lead.id, lead.photo_urls, {
        "address": lead.address,
        "price": lead.price,
        "beds": lead.beds,
        "baths": lead.baths,
        "sqft": lead.sqft,
    })
    return {"success": True, "message": "Full video generation started"}

@router.post("/generate-full-sync/{lead_id}", response_model=VideoGenerateResponse)
def generate_full_sync(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    try:
        video_path = video_gen.generate_full(lead.id, lead.photo_urls, {
            "address": lead.address,
            "price": lead.price,
            "beds": lead.beds,
            "baths": lead.baths,
            "sqft": lead.sqft,
        })
        video_filename = Path(video_path).name
        video_url = f"/videos/{video_filename}"
        # Update lead: full video ready, but conversion pending payment
        lead.full_video_url = video_url
        db.commit()
        return {"success": True, "message": "Full video generated", "video_url": video_url}
    except Exception as e:
        raise HTTPException(500, str(e))

# Background tasks
def generate_and_store_video(lead_id: int, listing_data: dict):
    try:
        video_path = video_gen.generate_teaser(lead_id, listing_data["photo_urls"], listing_data)
    except Exception as e:
        print(f"Video generation failed for lead {lead_id}: {e}")

def generate_full_task(lead_id: int, photo_urls: list, listing_data: dict):
    from app.models.models import SessionLocal
    db = SessionLocal()
    try:
        lead = db.query(Lead).get(lead_id)
        if not lead:
            return
        video_path = video_gen.generate_full(lead_id, photo_urls, listing_data)
        video_filename = Path(video_path).name
        video_url = f"/videos/{video_filename}"
        lead.full_video_url = video_url
        # Do NOT mark converted here; conversion happens after payment via Stripe webhook
        db.commit()
    except Exception as e:
        print(f"Full video generation failed for lead {lead_id}: {e}")
    finally:
        db.close()

def send_teaser_email_task(lead_id: int):
    from app.models.models import SessionLocal
    db = SessionLocal()
    try:
        lead = db.query(Lead).get(lead_id)
        if not lead:
            return
        if not lead.photo_urls:
            return
        # Generate teaser video if not exists
        video_path = video_gen.generate_teaser(lead.id, lead.photo_urls, {
            "address": lead.address,
            "price": lead.price,
            "beds": lead.beds,
            "baths": lead.baths,
            "sqft": lead.sqft,
        })
        video_filename = Path(video_path).name
        video_url = f"/videos/{video_filename}"
        # Send email
        email_service.send_teaser_email(
            to_email=lead.agent_email,
            to_name=lead.agent_name or "Agent",
            lead_id=lead.id,
            video_url=video_url
        )
        lead.email_sent_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        print(f"Email send failed: {e}")
    finally:
        db.close()
