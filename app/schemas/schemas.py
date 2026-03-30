"""Pydantic schemas for API"""
from pydantic import BaseModel, EmailStr, HttpUrl
from datetime import datetime
from typing import List, Optional

class LeadBase(BaseModel):
    listing_url: str
    platform: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    price: Optional[float] = None
    beds: Optional[float] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    property_type: Optional[str] = None
    photo_urls: List[str] = []
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None
    agent_email: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    status: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    email_opened: Optional[bool] = None
    converted: Optional[bool] = None
    notes: Optional[str] = None

class LeadResponse(LeadBase):
    id: int
    created_at: datetime
    status: str
    email_sent_at: Optional[datetime] = None
    email_opened: Optional[bool] = False
    teaser_video_url: Optional[str] = None
    converted_at: Optional[datetime] = None
    converted_to_full_video: Optional[bool] = False
    full_video_url: Optional[str] = None

    class Config:
        from_attributes = True

class Metrics(BaseModel):
    total_leads: int
    emails_sent: int
    conversions: int
    revenue: float

class ScrapeRequest(BaseModel):
    url: str
    platform: str = "zillow"

class ScrapeResponse(BaseModel):
    success: bool
    lead: LeadResponse

class MessageResponse(BaseModel):
    success: bool
    message: str

class VideoGenerateResponse(BaseModel):
    success: bool
    message: str
    video_url: Optional[str] = None
