"""Payments router (Stripe)"""
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
import logging
import stripe
from app.core.config import settings
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus, SystemEvent
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

def log_event(db, event_type, source, lead_id=None, message=None, details=None):
    try:
        ev = SystemEvent(
            type=event_type,
            source=source,
            lead_id=lead_id,
            message=message,
            details=details,
        )
        db.add(ev)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
        db.rollback()

@router.post("/create-checkout-session/{lead_id}")
def create_checkout_session(lead_id: int):
    """Create a Stripe Checkout session for $250 upsell"""
    if not settings.STRIPE_SECRET_KEY or not settings.FRONTEND_URL:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not lead.teaser_video_url:
            raise HTTPException(status_code=400, detail="Lead has no teaser video")
        
        success_url = f"{settings.FRONTEND_URL}/dashboard?payment=success&lead_id={lead_id}"
        cancel_url = f"{settings.FRONTEND_URL}/dashboard/outreach?payment=cancelled"
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Realviax Cinematic Video',
                        'description': f'60-second cinematic video for {lead.address or "property"}',
                    },
                    'unit_amount': 25000,  # $250.00
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'lead_id': str(lead_id),
                'type': 'upsell_video'
            }
        )
        
        # Mark that invoice was sent
        lead.invoice_sent = True
        db.commit()
        
        return {'sessionId': session.id, 'url': session.url}
    finally:
        db.close()

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Handle Stripe webhook events"""
    payload = await request.body()
    
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"Stripe webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    db = SessionLocal()
    try:
        event_type = event['type']
        # Log raw Stripe event
        log_event(db, f"stripe.{event_type}", "stripe", lead_id=None, message=f"Stripe event {event_type}", details=event)
        
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            lead_id = int(session.get('metadata', {}).get('lead_id', 0))
            if lead_id:
                lead = db.query(Lead).filter_by(id=lead_id).first()
                if lead:
                    lead.converted_at = datetime.utcnow()
                    lead.payment_received = True
                    lead.converted_to_full_video = True
                    lead.status = LeadStatus.CONVERTED.value
                    # Store actual amount paid (in cents)
                    amount_total = session.get('amount_total')
                    if amount_total:
                        lead.payment_amount_cents = int(amount_total)
                    db.commit()
                    logger.info(f"Lead {lead_id} converted via Stripe")
                    log_event(db, "payment.succeeded", "stripe", lead_id=lead_id, message=f"Payment received for lead {lead_id}", details={"session_id": session['id']})
                    
                    # Trigger full video generation (async ideally)
                    try:
                        from app.services.video_service import generate_and_store_full_video
                        generate_and_store_full_video(lead_id)
                        log_event(db, "video.generated", "backend", lead_id=lead_id, message="Full video generated after payment", details={"type": "full"})
                    except Exception as e:
                        logger.error(f"Failed to generate full video for lead {lead_id}: {e}")
                        log_event(db, "error", "backend", lead_id=lead_id, message=f"Full video generation failed: {e}")
                else:
                    logger.warning(f"Stripe webhook: lead {lead_id} not found")
        return JSONResponse(content={'status': 'ok'})
    finally:
        db.close()
