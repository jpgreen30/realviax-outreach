"""
Realviax Outreach System Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database/leads.db")
    
    # Brevo (email)
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "noreply@realviax.com")
    BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Realviax Video")
    
    # Twilio (SMS)
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "+1234567890")
    
    # Scraping
    SCRAPE_DELAY_MIN = float(os.getenv("SCRAPE_DELAY_MIN", 2))
    SCRAPE_DELAY_MAX = float(os.getenv("SCRAPE_DELAY_MAX", 5))
    MAX_SCRAPES_PER_DAY = int(os.getenv("MAX_SCRAPES_PER_DAY", 100))
    USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Video
    VIDEO_OUTPUT_DIR = os.getenv("VIDEO_OUTPUT_DIR", "output/videos")
    VIDEO_TEMPLATE_TEASER = os.getenv("VIDEO_TEMPLATE_TEASER", "templates/teaser.json")
    VIDEO_TEMPLATE_FULL = os.getenv("VIDEO_TEMPLATE_FULL", "templates/full.json")
    LOGO_PATH = os.getenv("LOGO_PATH", "assets/logo.png")
    MUSIC_DIR = os.getenv("MUSIC_DIR", "assets/music")
    
    # Outreach
    EMAIL_TEMPLATE_TEASER = os.getenv("EMAIL_TEMPLATE_TEASER", "templates/teaser_email.html")
    EMAIL_TEMPLATE_UPSELL = os.getenv("EMAIL_TEMPLATE_UPSELL", "templates/upsell_email.html")
    SMS_TEMPLATE = os.getenv("SMS_TEMPLATE", "templates/sms_templates.json")
    
    # Pricing
    TEASER_PRICE = 0  # free
    FULL_VIDEO_PRICE = 250  # $250 for 60s
    
    # Dashboard
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8000))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()