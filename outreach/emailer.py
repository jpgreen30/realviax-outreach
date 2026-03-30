"""
Brevo (Sendinblue) email sender with tracking
"""
import os
import requests
import logging
from typing import Dict, Any, Optional
from jinja2 import Template

logger = logging.getLogger(__name__)

class BrevoEmailer:
    API_URL = "https://api.brevo.com/v3"
    
    def __init__(self, api_key: str, sender_email: str, sender_name: str):
        self.api_key = api_key
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json"
        })
    
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        template_id: Optional[int] = None,
        template_vars: Optional[Dict] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an email via Brevo"""
        
        payload = {
            "sender": {
                "email": self.sender_email,
                "name": self.sender_name
            },
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html_content,
        }
        
        if reply_to:
            payload["replyTo"] = {"email": reply_to}
        
        if template_id and template_vars:
            payload["templateId"] = template_id
            payload["params"] = template_vars
        
        try:
            response = self.session.post(f"{self.API_URL}/smtp/email", json=payload)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Email sent to {to_email}: messageId={data.get('messageId')}")
            return {
                "success": True,
                "message_id": data.get("messageId"),
                "data": data
            }
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_smtp_template(self, template_id: int) -> Dict:
        """Fetch a transactional template"""
        response = self.session.get(f"{self.API_URL}/smtpl/templates/{template_id}")
        response.raise_for_status()
        return response.json()
    
    def create_smtp_template(self, name: str, html_content: str, subject: str) -> Dict:
        """Create a new transactional template"""
        payload = {
            "name": name,
            "subject": subject,
            "htmlContent": html_content,
            "isActive": True
        }
        response = self.session.post(f"{self.API_URL}/smtpl/templates", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_email_events(self, message_id: str) -> list:
        """Get tracking events for a sent email (opens, clicks, etc)"""
        # Brevo's event webhook is better for real-time, but we can poll
        # This is a simplified version - in production, use webhooks
        response = self.session.get(
            f"{self.API_URL}/smtp/statistics/events",
            params={"messageId": message_id, "limit": 10}
        )
        if response.status_code == 200:
            return response.json().get("events", [])
        return []
    
class EmailRenderer:
    """Render email templates with context"""
    
    @staticmethod
    def render_teaser_email(
        agent_name: str,
        listing_address: str,
        video_url: str,
        listing_data: Dict,
        unsubscribe_link: str
    ) -> str:
        """Render the initial teaser email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1a1a2e; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .video {{ margin: 30px 0; text-align: center; }}
                .video img {{ max-width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
                .cta {{ display: inline-block; background: #2563eb; color: white; padding: 15px 30px; 
                        text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
                .footer {{ margin-top: 30px; color: #666; font-size: 12px; text-align: center; }}
                .price {{ font-size: 28px; color: #059669; font-weight: bold; margin: 10px 0; }}
                .details {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }}
                .detail-box {{ background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
                .detail-value {{ font-size: 18px; font-weight: bold; }}
                .detail-label {{ font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏠 Exclusive Listing Video</h1>
            </div>
            <div class="content">
                <p>Hi {agent_name},</p>
                <p>I've created a premium 30-second cinematic teaser video for your listing at <strong>{listing_address}</strong>. Check it out below:</p>
                
                <div class="video">
                    <a href="{video_url}">
                        <img src="{video_url}" alt="Listing Video Preview" width="540" height="960">
                    </a>
                    <p style="font-style: italic; color: #666;">(Tap to play full video)</p>
                </div>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p class="price">
                        {listing_data.get('price_display', '$750,000')}
                    </p>
                    <div class="details">
                        <div class="detail-box">
                            <div class="detail-value">{listing_data.get('beds', '3')}</div>
                            <div class="detail-label">Bedrooms</div>
                        </div>
                        <div class="detail-box">
                            <div class="detail-value">{listing_data.get('baths', '2')}</div>
                            <div class="detail-label">Bathrooms</div>
                        </div>
                        <div class="detail-box">
                            <div class="detail-value">{listing_data.get('sqft', '2,500')}</div>
                            <div class="detail-label">Sq Ft</div>
                        </div>
                    </div>
                    <p style="margin-top: 15px;">{listing_address}</p>
                </div>
                
                <p>Loved the teaser? I can produce a <strong>full 60-second premium version</strong> with enhanced effects, professional voiceover, and multi-platform optimization for <strong>$250</strong>.</p>
                
                <div style="text-align: center;">
                    <a href="https://realviax.com/order?listing={listing_data.get('id', '')}" class="cta">
                        Get the Full 60-Second Video – $250
                    </a>
                </div>
                
                <p>Or reply to this email with any questions!</p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                
                <div class="footer">
                    <p>This is a personalized video offer for your listing. Video created by Realviax.</p>
                    <p><a href="{unsubscribe_link}">Unsubscribe</a> | <a href="https://realviax.com">realviax.com</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def render_upsell_email(
        agent_name: str,
        listing_address: str,
        full_video_url: str,
        invoice_link: str
    ) -> str:
        """Render upsell email with full 60s video"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1a1a2e; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .video {{ margin: 30px 0; text-align: center; }}
                .video img {{ max-width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
                .cta {{ display: inline-block; background: #059669; color: white; padding: 15px 30px; 
                        text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
                .features {{ margin: 20px 0; }}
                .feature {{ margin: 10px 0; padding: 10px; background: white; border-radius: 6px; }}
                .price {{ font-size: 32px; color: #059669; font-weight: bold; text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎬 Your Premium Listing Video is Ready</h1>
            </div>
            <div class="content">
                <p>Hi {agent_name},</p>
                <p>Based on your response, I've upgraded your video for <strong>{listing_address}</strong> to the full 60-second premium version. Here's the final product:</p>
                
                <div class="video">
                    <a href="{full_video_url}">
                        <img src="{full_video_url}" alt="Premium Video" width="540" height="1080">
                    </a>
                </div>
                
                <h3 style="margin-top: 30px;">Premium Features Included:</h3>
                <div class="features">
                    <div class="feature">✅ 60-second runtime (double the exposure)</div>
                    <div class="feature">✅ Hollywood-grade color grading</div>
                    <div class="feature">✅ Professional voiceover (male/female options)</div>
                    <div class="feature">✅ Custom soundtrack with proper licensing</div>
                    <div class="feature">✅ Optimized for Instagram, TikTok, Facebook, YouTube</div>
                    <div class="feature">✅ Source file included for future edits</div>
                </div>
                
                <div class="price">$250 USD</div>
                <p style="text-align: center; color: #666;">One-time payment, full rights to use</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invoice_link}" class="cta">Pay Invoice & Receive Source File</a>
                </div>
                
                <p>Once payment is received, I'll send you the high-resolution video file and all source materials. Payment can be made via PayPal, Venmo, or bank transfer.</p>
                
                <p>Reply with any questions!</p>
            </div>
        </body>
        </html>
        """
        return html