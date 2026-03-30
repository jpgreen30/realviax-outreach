#!/usr/bin/env python3
"""
Test full pipeline: Create test lead → generate video → send email
"""
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

# Add project to path (use run.py's inline models since DB matches that)
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3

# Direct DB access - schema matches run.py
DB_PATH = "leads.db"

def create_test_lead():
    """Insert a test lead with real photo URLs"""
    test_data = {
        "listing_url": "https://www.zillow.com/homedetails/123-Test-St-Los-Angeles-CA/123456_test/",
        "platform": "zillow",
        "address": "123 Test Street, Beverly Hills, CA 90210",
        "city": "Beverly Hills",
        "state": "CA",
        "zip_code": "90210",
        "price": 3250000.0,
        "beds": 5.0,
        "baths": 4.5,
        "sqft": 4200,
        "agent_name": "Test Agent",
        "agent_email": "test.agent@example.com",  # Use test email
        "agent_phone": "+13105551234",
        "photo_urls": '["https://images.unsplash.com/photo-1564013799919-ab6000a2e3c8?w=1080&h=1920&fit=crop","https://images.unsplash.com/photo-1600596542815-e32c1ee2ac97?w=1080&h=1920&fit=crop","https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1080&h=1920&fit=crop"]',
        "status": "scraped",
        "converted": 0,
        "email_opened": 0,
        "notes": "Test lead for pipeline"
    }
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if exists
    cur.execute("SELECT id FROM leads WHERE listing_url = ?", (test_data['listing_url'],))
    existing = cur.fetchone()
    if existing:
        lead_id = existing[0]
        print(f"Lead already exists with ID {lead_id}")
        conn.close()
        return lead_id
    
    # Insert
    cols = ', '.join(test_data.keys())
    placeholders = ', '.join(['?' for _ in test_data])
    values = list(test_data.values())
    cur.execute(f"INSERT INTO leads ({cols}) VALUES ({placeholders})", values)
    lead_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    print(f"Created test lead ID: {lead_id}")
    return lead_id

def test_pipeline(lead_id):
    """Run full pipeline: generate video → send email"""
    base_url = "http://localhost:8000"
    
    # 1. Generate Video
    print("\n🎬 Generating video...")
    resp = requests.post(f"{base_url}/api/generate/{lead_id}")
    if resp.status_code == 200:
        print(f"   ✓ Video generation started: {resp.json()}")
    else:
        print(f"   ✗ Video generation failed: {resp.status_code} - {resp.text}")
        return False
    
    # Wait a few seconds for generation (since it's background)
    import time
    print("   Waiting 5 seconds for video generation...")
    time.sleep(5)
    
    # 2. Send Email
    print("\n📧 Sending email...")
    resp = requests.post(f"{base_url}/api/send-email/{lead_id}")
    if resp.status_code == 200:
        print(f"   ✓ Email sent: {resp.json()}")
    else:
        print(f"   ✗ Email failed: {resp.status_code} - {resp.text}")
        return False
    
    # 3. Check metrics
    print("\n📊 Checking metrics...")
    resp = requests.get(f"{base_url}/api/metrics")
    if resp.status_code == 200:
        metrics = resp.json()
        print(f"   Metrics: {metrics}")
    else:
        print(f"   ✗ Failed to get metrics")
    
    # 4. Check lead status
    print("\n🔍 Checking lead status...")
    resp = requests.get(f"{base_url}/api/leads?limit=5")
    if resp.status_code == 200:
        leads = resp.json()
        for lead in leads:
            if lead['id'] == lead_id:
                print(f"   Lead: {lead}")
                break
    else:
        print(f"   ✗ Failed to get leads")
    
    return True

def main():
    print("=" * 60)
    print("🧪 REALVIAX OUTREACH - FULL PIPELINE TEST")
    print("=" * 60)
    
    # Create test lead
    lead_id = create_test_lead()
    
    # Run pipeline
    success = test_pipeline(lead_id)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ PIPELINE TEST COMPLETE")
    else:
        print("⚠️  PIPELINE TEST COMPLETED WITH ISSUES")
    print("=" * 60)
    
    print("\nNext steps:")
    print("- Check output/videos/ for generated video")
    print("- Verify email was sent via Brevo dashboard")
    print("- Review lead tracking in database")
    print("- Add proper logo at assets/logo.png")
    print("- Add background music to assets/music/")
    print("- Set up video hosting (S3/CloudFront) for public URLs")

if __name__ == "__main__":
    main()
