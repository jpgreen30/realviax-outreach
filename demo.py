#!/usr/bin/env python3
"""
Realviax Outreach - Demo Mode

Runs the full workflow with mock data (no external APIs).
Demonstrates:
- Scraping simulation
- Video generation with real ffmpeg
- Email preview
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

def demo_scrape():
    """Simulate scraping a listing"""
    print("🔍 [SCRAPER] Simulating scrape of Zillow listing...")
    mock_data = {
        "platform": "zillow",
        "listing_url": "https://www.zillow.com/homedetails/123-Main-St/12345_zpid/",
        "address": "123 Main St, Beverly Hills, CA 90210",
        "city": "Beverly Hills",
        "state": "CA",
        "zip_code": "90210",
        "price": 3250000,
        "beds": 5,
        "baths": 4.5,
        "sqft": 4200,
        "property_type": "Single Family",
        "agent_name": "John Smith",
        "agent_email": "john.smith@realty.com",
        "agent_phone": "(310) 555-1234",
        "photo_urls": [
            "https://example.com/photo1.jpg",
            "https://example.com/photo2.jpg",
            "https://example.com/photo3.jpg",
        ]
    }
    print(f"   ✓ Scraped: {mock_data['address']}")
    print(f"   ✓ Agent: {mock_data['agent_name']} ({mock_data['agent_email']})")
    print(f"   ✓ Photos: {len(mock_data['photo_urls'])} images")
    return mock_data

def demo_video_generate(listing_data):
    """Generate actual teaser video (30s) with placeholder images"""
    from video.generator import VideoGenerator
    import requests
    from PIL import Image, ImageDraw
    
    print("\n🎬 [VIDEO] Generating 30-second teaser...")
    
    # Create some placeholder images if we can't download
    work_dir = Path("output/demo_work")
    work_dir.mkdir(parents=True, exist_ok=True)
    photo_dir = work_dir / "photos"
    photo_dir.mkdir(exist_ok=True)
    
    # Create 3 sample vertical images
    W, H = 1080, 1920
    colors = [(99,102,241), (234,88,12), (16,185,129)]
    for i, color in enumerate(colors):
        img = Image.new('RGB', (W, H), color)
        d = ImageDraw.Draw(img)
        d.text((W//2, H//2), f"Scene {i+1}", fill='white', anchor="mm", size=60)
        img.save(photo_dir / f"photo_{i}.jpg")
    
    # Use these local images instead of URLs
    listing_data['photo_urls'] = [str(photo_dir / f"photo_{i}.jpg") for i in range(3)]
    
    gen = VideoGenerator(
        logo_path="assets/logo.png",
        music_dir="assets/music",
        output_dir="output/videos"
    )
    
    try:
        output_path = gen.generate_teaser(
            listing_data=listing_data,
            photo_urls=listing_data['photo_urls']
        )
        print(f"   ✓ Teaser video created: {output_path}")
        print(f"   ✓ File size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
        return output_path
    except Exception as e:
        print(f"   ✗ Video generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def demo_email(agent_name, listing_address, video_path):
    """Show email preview"""
    print("\n📧 [EMAIL] Preparing teaser email...")
    
    # In a real run, video_path would be uploaded to CDN
    # Here we just show a relative path
    video_url = f"https://cdn.realviax.com/videos/{Path(video_path).name}" if video_path else "https://example.com/video.mp4"
    
    # Render a sample email
    html = f"""
    <html>
    <body style="font-family: Arial; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: white; padding: 20px; text-align: center;">
            <h1>🏠 Exclusive Listing Video</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <p>Hi {agent_name},</p>
            <p>I've created a premium 30-second cinematic teaser video for your listing at <strong>{listing_address}</strong>.</p>
            <p><a href="{video_url}">▶️ Watch Video</a></p>
            <p>Loved the teaser? I can produce a full 60-second premium version for <strong>$250</strong>.</p>
            <p><a href="https://realviax.com/order" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">Get Full Video – $250</a></p>
        </div>
    </body>
    </html>
    """
    
    # Save preview
    preview_path = Path("output/email_preview.html")
    with open(preview_path, 'w') as f:
        f.write(html)
    print(f"   ✓ Email HTML preview saved: {preview_path}")
    print("   ✓ (In production, would send via Brevo API)")
    return html

def demo_track(listing_url):
    """Show tracking entry"""
    print("\n📊 [TRACKING] Logging lead and video generation...")
    print(f"   ✓ Lead: {listing_url}")
    print("   ✓ Status: email_sent")
    print("   ✓ Video: teaser type")
    print("   ✓ Metrics: will be available in dashboard")
    return True

def main():
    print("=" * 60)
    print("🎬 REALVIAX OUTREACH - DEMO MODE")
    print("=" * 60)
    
    # Ensure directories exist
    os.makedirs("output/videos", exist_ok=True)
    os.makedirs("assets/music", exist_ok=True)
    
    # Check logo exists
    if not os.path.exists("assets/logo.png"):
        print("⚠️  Warning: assets/logo.png not found. Video will be generated without watermark.")
        print("   Place your logo file at: realviax-outreach/assets/logo.png")
    
    # Run demo
    data = demo_scrape()
    video = demo_video_generate(data)
    if video:
        demo_email(data['agent_name'], data['address'], video)
        demo_track(data['listing_url'])
    
    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETE")
    print("=" * 60)
    print("\nWhat happened:")
    print("1. Simulated scrape of a listing (mocked data)")
    print("2. Generated actual 30-second video with ffmpeg")
    print("3. Created email HTML preview")
    print("4. Tracked lead in database (would be real in full version)")
    
    print("\n\nTo run in production:")
    print("1. Fill in config/.env with your Brevo & Twilio API keys")
    print("2. Add your logo to assets/logo.png")
    print("3. Add royalty-free music to assets/music/")
    print("4. Run: python3 main.py --dashboard")
    print("5. Or process real URLs: python3 main.py --url 'https://...' --platform zillow")

if __name__ == "__main__":
    main()