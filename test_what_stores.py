#!/usr/bin/env python3
"""Test what SQLEnum stores by default"""
import os, sys
from sqlalchemy import create_engine, Column, Integer, Enum as SQLEnum
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
    __tablename__ = "enum_test"
    id = Column(Integer, primary_key=True)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.SCRAPED)

engine = create_engine("sqlite:///enum_test.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Insert a row using ORM
with Session() as s:
    lead = Lead()
    s.add(lead)
    s.commit()
    print(f"Created lead with status: {lead.status} (value: {lead.status.value})")

# Check what's in the DB
import sqlite3
conn = sqlite3.connect("enum_test.db")
cur = conn.cursor()
cur.execute("SELECT id, status FROM enum_test")
row = cur.fetchone()
print(f"Raw DB value: {row[1]}")
conn.close()
