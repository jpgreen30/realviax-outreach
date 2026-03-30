"""
Twilio SMS sender with tracking
"""
import os
from twilio.rest import Client
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TwilioTexter:
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
    
    def send_sms(
        self,
        to_number: str,
        message: str,
        media_urls: Optional[list] = None
    ) -> Dict[str, Any]:
        """Send SMS (optionally with MMS media)"""
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number,
                media_url=media_urls or []
            )
            
            logger.info(f"SMS sent to {to_number}: SID={msg.sid}")
            return {
                "success": True,
                "sid": msg.sid,
                "status": msg.status,
                "date_sent": msg.date_sent
            }
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_teaser_sms(
        self,
        to_name: str,
        to_number: str,
        video_url: str,
        listing_address: str,
        price: str
    ) -> Dict[str, Any]:
        """Send a templated teaser SMS with video link"""
        message = f"""Hi {to_name}, I've created a cinematic teaser video for your listing at {listing_address}. View it here: {video_url}

Like it? I can produce a full 60-second premium version for $250. Reply for details."""
        
        return self.send_sms(
            to_number=to_number,
            message=message.strip(),
            media_urls=[video_url] if video_url.startswith('http') else None
        )
    
    def send_followup_sms(
        self,
        to_name: str,
        to_number: str,
        listing_address: str,
        full_video_url: str,
        invoice_link: str
    ) -> Dict[str, Any]:
        """Send follow-up with full video and invoice"""
        message = f"""Hi {to_name}, your premium 60-second video for {listing_address} is ready: {full_video_url}

Pay $250 via this invoice: {invoice_link}

Payment unlocks the high-res source file. Questions? Reply anytime."""
        
        return self.send_sms(
            to_number=to_number,
            message=message.strip(),
            media_urls=[full_video_url] if full_video_url.startswith('http') else None
        )