"""Core configuration"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database: use Supabase PostgreSQL for production
    DATABASE_URL: str = "sqlite:///leads.db"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "videos"

    # Video storage
    VIDEO_OUTPUT_DIR: str = "output/videos"
    LOGO_PATH: str = "assets/logo.png"
    MUSIC_DIR: str = "assets/music"

    # Brevo
    BREVO_API_KEY: Optional[str] = None
    BREVO_SENDER_EMAIL: Optional[str] = None
    BREVO_SENDER_NAME: str = "Realviax Video"
    BREVO_WEBHOOK_SECRET: Optional[str] = None

    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None

    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    FRONTEND_URL: Optional[str] = None

    # Scraping
    SCRAPE_DELAY_MIN: int = 2
    SCRAPE_DELAY_MAX: int = 5
    MAX_SCRAPES_PER_DAY: int = 100

    # Scheduler
    SCRAPER_CRON_HOUR: int = 6   # 6 AM UTC daily
    SCRAPER_CRAP_MIN: int = 0

    # Public backend URL for links (e.g., in emails)
    PUBLIC_URL: Optional[str] = None  # e.g., https://api.realviax.com

    class Config:
        env_file = ".env"

settings = Settings()
