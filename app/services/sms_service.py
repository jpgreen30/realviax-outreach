from twilio.rest import Client
from app.core.config import settings

class SMSService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER
        self.client = None
        if all([self.account_sid, self.auth_token, self.from_number]):
            self.client = Client(self.account_sid, self.auth_token)

    def send_teaser_sms(self, to_phone: str, to_name: str, video_url: str) -> dict:
        if not self.client:
            raise RuntimeError("Twilio not configured")
        message = f"Hi {to_name}, your teaser video is ready: {video_url}. Upgrade to full 60s cinematic for $250."
        msg = self.client.messages.create(
            body=message,
            from_=self.from_number,
            to=to_phone
        )
        return {"sid": msg.sid, "status": msg.status}

sms_service = SMSService()
