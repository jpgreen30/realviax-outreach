#!/usr/bin/env python3
"""Check if ORM sees the leads"""
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from enum import Enum

# Same as run.py
Base = declarative_base()

class LeadStatus(str, Enum):
    SCRAPED = "scraped"
    EMAIL_SENT = "email_sent"
    CONVERTED = "converted"

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    listing_url = Column(String, unique=True, nullable=False, index=True)
    platform = Column(String, nullable=False)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    price = Column(Float)
    beds = Column(Float)
    baths = Column(Float)
    sqft = Column(Integer)
    agent_name = Column(String)
    agent_email = Column(String)
    agent_phone = Column(String)
    photo_urls = Column(JSON, default=list)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.SCRAPED)
    email_sent_at = Column(DateTime)
    email_opened = Column(Boolean, default=False)
    converted = Column(Boolean, default=False)
    notes = Column(Text)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///leads.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

with SessionLocal() as db:
    count = db.query(Lead).count()
    print(f"Lead count via ORM: {count}")
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(5).all()
    for l in leads:
        print(f"ID={l.id} addr={l.address} status={l.status}")
