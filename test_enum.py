#!/usr/bin/env python3
"""Reproduce the enum issue"""
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SQLEnum, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from enum import Enum

Base = declarative_base()

class LeadStatus(str, Enum):
    SCRAPED = "scraped"
    EMAIL_SENT = "email_sent"
    CONVERTED = "converted"

class Lead(Base):
    __tablename__ = "leads_test"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.SCRAPED)

# Use in-memory SQLite
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

# Insert a row with status='scraped' using raw SQL to simulate our manual insert
with engine.connect() as conn:
    conn.execute(text("INSERT INTO leads_test (status) VALUES ('scraped')"))
    conn.commit()

# Now query via ORM
with SessionLocal() as db:
    try:
        lead = db.query(Lead).first()
        print(f"Lead status: {lead.status}")
        print(f"Type: {type(lead.status)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
