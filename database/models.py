"""
Database models for lead tracking and campaign management
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import enum

Base = declarative_base()

class LeadStatus(enum.Enum):
    SCRAPED = "scraped"
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    REPLIED = "replied"
    CONVERTED = "converted"
    SMS_SENT = "sms_sent"
    SMS_REPLIED = "sms_replied"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"

class Platform(enum.Enum):
    ZILLOW = "zillow"
    REDFIN = "redfin"
    REALTOR_COM = "realtor_com"
    OTHER = "other"

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Listing info
    listing_url = Column(String, unique=True, nullable=False, index=True)
    platform = Column(SQLEnum(Platform), nullable=False)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    price = Column(Float)
    beds = Column(Float)
    baths = Column(Float)
    sqft = Column(Integer)
    property_type = Column(String)
    photo_urls = Column(JSON)  # List of image URLs
    
    # Agent info
    agent_name = Column(String)
    agent_phone = Column(String)
    agent_email = Column(String)
    office_name = Column(String)
    
    # Status
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.SCRAPED)
    
    # Outreach tracking
    email_sent_at = Column(DateTime)
    email_id = Column(String)  # Brevo message ID
    email_opened = Column(Boolean, default=False)
    email_opened_at = Column(DateTime)
    email_clicked = Column(Boolean, default=False)
    email_clicked_at = Column(DateTime)
    email_reply_count = Column(Integer, default=0)
    
    sms_sent_at = Column(DateTime)
    sms_sid = Column(String)  # Twilio message SID
    sms_replied = Column(Boolean, default=False)
    
    # Conversion
    converted_at = Column(DateTime)
    converted_to_full_video = Column(Boolean, default=False)
    full_video_url = Column(String)
    invoice_sent = Column(Boolean, default=False)
    payment_received = Column(Boolean, default=False)
    
    # Notes
    notes = Column(Text)
    
    # Relationships
    videos = relationship("Video", back_populates="lead")
    outreach_logs = relationship("OutreachLog", back_populates="lead")

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    lead_id = Column(Integer, ForeignKey("leads.id"))
    video_type = Column(String, nullable=False)  # "teaser" or "full"
    duration = Column(Integer, default=30)  # seconds
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)  # bytes
    width = Column(Integer, default=1080)
    height = Column(Integer, default=1920)
    
    # Rendering metadata
    render_time_seconds = Column(Integer)
    used_photos = Column(JSON)  # List of photo paths used
    
    # Sharing
    hosted_url = Column(String)  # S3/CDN URL if uploaded
    
    lead = relationship("Lead", back_populates="videos")

class OutreachLog(Base):
    __tablename__ = "outreach_logs"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    lead_id = Column(Integer, ForeignKey("leads.id"))
    channel = Column(String, nullable=False)  # "email" or "sms"
    direction = Column(String, default="outbound")
    template_used = Column(String)
    message_sid = Column(String)  # Provider message ID
    status = Column(String)  # "sent", "delivered", "opened", "clicked", "bounced", "failed"
    
    # Tracking
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)
    
    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    extra_data = Column(JSON)  # Additional provider data
    
    lead = relationship("Lead", back_populates="outreach_logs")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Filters
    platforms = Column(JSON, default=list)  # List of platforms to target
    min_price = Column(Float)
    max_price = Column(Float)
    cities = Column(JSON, default=list)
    states = Column(JSON, default=list)
    
    # Metrics
    leads_scraped = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    sms_sent = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    
    # Active status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    leads = relationship("Lead", secondary="campaign_leads", back_populates="campaigns")

# Association table for many-to-many Lead <-> Campaign
from sqlalchemy import Table
campaign_leads = Table(
    "campaign_leads", Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id"), primary_key=True),
    Column("lead_id", Integer, ForeignKey("leads.id"), primary_key=True)
)

# Add relationship to Lead
Lead.campaigns = relationship("Campaign", secondary=campaign_leads, back_populates="leads")

def init_db(engine=None):
    if engine is None:
        # Use default SQLite in current directory
        engine = create_engine("sqlite:///leads.db")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)