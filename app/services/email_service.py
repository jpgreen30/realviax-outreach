import os
import logging
from datetime import datetime
import requests
from app.core.config import settings
from app.utils.db import SessionLocal
from app.models.models import Lead, OutreachLog

logger = logging.getLogger(__name__)

class EmailService:
    BASE_URL = "https://api.brevo.com/v3"

    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        self.sender_email = settings.BREVO_SENDER_EMAIL
        self.sender_name = settings.BREVO_SENDER_NAME

    def send_teaser_email(self, to_email: str, to_name: str, lead_id: int, video_url: str, checkout_url: str = None) -> dict:
        """Send an email with a teaser video and upsell offer."""
        if not self.api_key:
            raise RuntimeError("Brevo API key not configured")

        url = f"{self.BASE_URL}/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json",
        }
        # Use provided checkout URL or fallback to '#'
        upgrade_link = checkout_url or "#"
        payload = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [{"email": to_email, "name": to_name}],
            "subject": "Your teaser video is ready + special offer",
            "htmlContent": f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; background:#f8f8f8; margin:0; padding:0;">
              <div style="max-width:600px; margin:0 auto; background:#fff; padding:20px;">
                <h2 style="color:#1a1a2e;">Your teaser video is ready!</h2>
                <p>Hello {to_name},</p>
                <p>We've created a 30-second teaser video for your listing. View it here:</p>
                <p style="text-align:center; margin:20px 0;">
                  <a href="{video_url}" style="background:#1a1a2e; color:#fff; padding:12px 24px; text-decoration:none; border-radius:4px;">Watch Teaser</a>
                </p>
                <p>Want the full 60-second cinematic version? Upgrade for $250 and get:</p>
                <ul>
                  <li>Longer, more cinematic edit</li>
                  <li>Branded & unbranded versions</li>
                  <li>Social media cuts</li>
                  <li>CTA end card</li>
                </ul>
                <p style="text-align:center; margin:20px 0;">
                  <a href="{upgrade_link}" style="background:#10b981; color:#ffffff; padding:12px 24px; text-decoration:none; border-radius:4px; font-weight:bold;">Upgrade to Pro</a>
                </p>
                <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                <p style="color:#888; font-size:12px;">Sent by Realviax Outreach</p>
              </div>
            </body>
            </html>
            """,
            "params": {"lead_id": lead_id},
            "tracking_settings": {
                "open": True,
                "click": True,
                "text_open": False
            }
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        # Log outreach outbound
        db = SessionLocal()
        try:
            log = OutreachLog(
                lead_id=lead_id,
                channel="email",
                direction="outbound",
                template_used="teaser_upsell",
                message_sid=result.get('messageId'),
                status="sent",
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to create OutreachLog: {e}")
            db.rollback()
        finally:
            db.close()
        return result

email_service = EmailService()

def create_stripe_checkout_session(lead_id: int, amount_override: int = None) -> str:
    """Create Stripe checkout session and return URL, or None if not configured.
    amount_override: optional price in USD (e.g., 199 for $1.99). Default 250 ($250).
    """
    if not settings.STRIPE_SECRET_KEY or not settings.FRONTEND_URL:
        return None
    import stripe
    from app.utils.db import SessionLocal
    from app.models.models import Lead
    stripe.api_key = settings.STRIPE_SECRET_KEY
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead or not lead.teaser_video_url:
            return None
        success_url = f"{settings.FRONTEND_URL}/dashboard?payment=success&lead_id={lead_id}"
        cancel_url = f"{settings.FRONTEND_URL}/dashboard/outreach?payment=cancelled"
        unit_cents = int((amount_override if amount_override else 250) * 100)
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Realviax Cinematic Video',
                        'description': f'60-second cinematic video for {lead.address or "property"}',
                    },
                    'unit_amount': unit_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={'lead_id': str(lead_id), 'type': 'upsell_video', 'discount': str(amount_override) if amount_override else 'none'}
        )
        # Mark invoice sent
        lead.invoice_sent = True
        db.commit()
        return session.url
    finally:
        db.close()

def send_outreach_emails(limit: int = 200) -> int:
    """Send teaser emails to all scraped leads with generated teaser videos."""
    from app.utils.db import SessionLocal
    from app.models.models import Lead
    db = SessionLocal()
    try:
        leads = db.query(Lead).filter(
            Lead.teaser_video_url != None,
            Lead.email_sent_at == None,
            Lead.agent_email != None,
        ).all()
        sent = 0
        for lead in leads:
            try:
                # Build absolute video URL
                video_path = lead.teaser_video_url
                if video_path.startswith('/'):
                    base = settings.PUBLIC_URL or settings.FRONTEND_URL or "http://localhost:8000"
                    video_url = f"{base.rstrip('/')}{video_path}"
                else:
                    video_url = video_path
                # Create checkout URL if Stripe configured
                checkout_url = None
                try:
                    checkout_url = create_stripe_checkout_session(lead.id)
                except Exception as e:
                    logger.warning(f"Stripe checkout creation failed for lead {lead.id}: {e}")
                result = email_service.send_teaser_email(
                    to_email=lead.agent_email,
                    to_name=lead.agent_name or "Agent",
                    lead_id=lead.id,
                    video_url=video_url,
                    checkout_url=checkout_url
                )
                lead.email_sent_at = datetime.utcnow()
                lead.email_id = result.get('messageId')
                db.commit()
                sent += 1
                logger.info(f"Sent teaser email to lead {lead.id} ({lead.agent_email})")
            except Exception as e:
                logger.error(f"Failed to send email to lead {lead.id}: {e}")
                db.rollback()
        return sent
    finally:
        db.close()