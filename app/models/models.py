"""Database models"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

class LeadStatus(str, enum.Enum):
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

class Platform(str, enum.Enum):
    ZILLOW = "zillow"
    REDFIN = "redfin"
    REALTOR_COM = "realtor_com"
    OTHER = "other"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    listing_url = Column(String, unique=True, nullable=False, index=True)
    platform = Column(String, nullable=False)  # store enum value
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    price = Column(Float)
    beds = Column(Float)
    baths = Column(Float)
    sqft = Column(Integer)
    property_type = Column(String)
    photo_urls = Column(JSON, default=list)

    agent_name = Column(String)
    agent_phone = Column(String)
    agent_email = Column(String)
    office_name = Column(String)

    status = Column(String, default=LeadStatus.SCRAPED.value)
    email_sent_at = Column(DateTime)
    email_id = Column(String)
    email_opened = Column(Boolean, default=False)
    email_opened_at = Column(DateTime)
    email_clicked = Column(Boolean, default=False)
    email_clicked_at = Column(DateTime)
    email_reply_count = Column(Integer, default=0)

    sms_sent_at = Column(DateTime)
    sms_sid = Column(String)
    sms_replied = Column(Boolean, default=False)

    teaser_video_url = Column(String)  # Path/URL to generated teaser
    converted_at = Column(DateTime)
    converted_to_full_video = Column(Boolean, default=False)
    full_video_url = Column(String)
    invoice_sent = Column(Boolean, default=False)
    payment_received = Column(Boolean, default=False)
    payment_amount_cents = Column(Integer, nullable=True)  # Actual amount paid in cents

    notes = Column(Text)

    def as_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "listing_url": self.listing_url,
            "platform": self.platform,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "price": self.price,
            "beds": self.beds,
            "baths": self.baths,
            "sqft": self.sqft,
            "property_type": self.property_type,
            "photo_urls": self.photo_urls or [],
            "agent_name": self.agent_name,
            "agent_phone": self.agent_phone,
            "agent_email": self.agent_email,
            "office_name": self.office_name,
            "status": self.status,
            "teaser_video_url": self.teaser_video_url,
            "full_video_url": self.full_video_url,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None,
            "payment_received": self.payment_received,
        }

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead_id = Column(Integer, ForeignKey("leads.id"))
    video_type = Column(String, nullable=False)  # "teaser" or "full"
    duration = Column(Integer, default=30)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    width = Column(Integer, default=1080)
    height = Column(Integer, default=1920)

    render_time_seconds = Column(Integer)
    used_photos = Column(JSON)

    hosted_url = Column(String)

    lead = relationship("Lead", back_populates="videos")

class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead_id = Column(Integer, ForeignKey("leads.id"))
    channel = Column(String, nullable=False)  # "email" or "sms"
    direction = Column(String, default="outbound")
    template_used = Column(String)
    message_sid = Column(String)
    status = Column(String)  # sent, delivered, opened, clicked, bounced, failed

    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)

    extra_data = Column(JSON)

    lead = relationship("Lead", back_populates="outreach_logs")

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(String, nullable=False, index=True)  # e.g., "email.open", "email.click", "stripe.payment", "video.generated", "error"
    source = Column(String, nullable=True)  # "brevo", "stripe", "scheduler", etc.
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    details = Column(JSON, nullable=True)
    message = Column(Text, nullable=True)

# ============== LANDING PAGES ==============
class LandingPage(Base):
    """ Personalized teaser page for a lead """
    __tablename__ = "landing_pages"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, unique=True)  # future-proof
    slug = Column(String, unique=True, nullable=False, index=True)
    teaser_video_url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    headline = Column(String, nullable=False)
    subheadline = Column(String, nullable=True)
    cta_text = Column(String, default="Claim Your Free Teaser")
    status = Column(String, default="active")  # active, inactive

class LandingPageSubmission(Base):
    """ Captured agent info from landing page form """
    __tablename__ = "landing_page_submissions"

    id = Column(Integer, primary_key=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)

    landing_page_id = Column(Integer, ForeignKey("landing_pages.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)  # may match existing lead

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)

    landing_page = relationship("LandingPage", backref="submissions")

# ============== ORDERS ==============
class Order(Base):
    """ Stripe payment tracking """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)  # if we add properties table; for now use lead_id
    stripe_checkout_session_id = Column(String, unique=True, nullable=True)
    stripe_payment_intent_id = Column(String, unique=True, nullable=True)
    product_name = Column(String, default="Premium Cinematic Video")
    amount = Column(Float, nullable=False)  # in USD
    currency = Column(String, default="usd")
    order_status = Column(String, default="pending")  # pending, paid, fulfilled, refunded
    paid_at = Column(DateTime, nullable=True)

    lead = relationship("Lead", backref="orders")

# Properties table to store detailed listing info (optional, but can be integrated with Lead)
class Property(Base):
    """ Detailed property information (can be extracted from listing) """
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True)
    listing_url = Column(String, nullable=False)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    price = Column(Float)
    beds = Column(Float)
    baths = Column(Float)
    sqft = Column(Integer)
    headline = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    features_json = Column(JSON, default=list)
    source_payload_json = Column(JSON, default=dict)

    lead = relationship("Lead", back_populates="property")

# Extend Lead to have backrefs
Lead.property = relationship("Property", uselist=False, back_populates="lead", cascade="all, delete-orphan")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    platforms = Column(JSON, default=list)
    min_price = Column(Float)
    max_price = Column(Float)
    cities = Column(JSON, default=list)
    states = Column(JSON, default=list)

    leads_scraped = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    sms_sent = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)

    is_active = Column(Boolean, default=True)

# Relationships
from sqlalchemy import Table
campaign_leads = Table(
    "campaign_leads", Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id"), primary_key=True),
    Column("lead_id", Integer, ForeignKey("leads.id"), primary_key=True)
)
Lead.campaigns = relationship("Campaign", secondary=campaign_leads, back_populates="leads")
Campaign.leads = relationship("Lead", secondary=campaign_leads, back_populates="campaigns")
Lead.videos = relationship("Video", back_populates="lead")
Video.lead = relationship("Lead", back_populates="videos")
Lead.outreach_logs = relationship("OutreachLog", back_populates="lead")
OutreachLog.lead = relationship("Lead", back_populates="outreach_logs")
Lead.system_events = relationship("SystemEvent", back_populates="lead", order_by="desc(SystemEvent.created_at)")
SystemEvent.lead = relationship("Lead", back_populates="system_events")

# Property relationship (one-to-one with Lead)
Lead.property = relationship("Property", uselist=False, back_populates="lead", cascade="all, delete-orphan")
Property.lead = relationship("Lead", back_populates="property")

# LandingPage relationship (one-to-one with Lead)
Lead.landing_page = relationship("LandingPage", uselist=False, back_populates="lead")
LandingPage.lead = relationship("Lead", back_populates="landing_page")

def init_db(engine_url: str = None):
    from app.core.config import settings
    engine = create_engine(engine_url or settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
