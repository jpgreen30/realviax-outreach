"""
Realviax Outreach Dashboard - FastAPI
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from config.settings import Settings

settings = Settings()
app = FastAPI(title="Realviax Outreach Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

# Database
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@app.get("/")
def index(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/metrics")
def get_metrics(days: int = 30):
    """Get campaign metrics"""
    with SessionLocal() as session:
        from datetime import datetime, timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Query metrics
        metrics = {
            "total_leads": session.execute(text("SELECT COUNT(*) FROM leads WHERE created_at >= :cutoff"), {"cutoff": cutoff}).scalar() or 0,
            "emails_sent": session.execute(text("""
                SELECT COUNT(*) FROM outreach_logs 
                WHERE channel='email' AND created_at >= :cutoff
            """), {"cutoff": cutoff}).scalar() or 0,
            "conversions": session.execute(text("""
                SELECT COUNT(*) FROM leads 
                WHERE status='converted' AND converted_at >= :cutoff
            """), {"cutoff": cutoff}).scalar() or 0,
        }
        
        # Calculate revenue (assuming $250 per conversion)
        metrics["revenue"] = metrics["conversions"] * 250
        
        # Open rate (simplified)
        if metrics["emails_sent"] > 0:
            opened = session.execute(text("""
                SELECT COUNT(*) FROM leads 
                WHERE email_opened = True AND email_opened_at >= :cutoff
            """), {"cutoff": cutoff}).scalar() or 0
            metrics["open_rate"] = opened / metrics["emails_sent"]
        else:
            metrics["open_rate"] = 0
        
        return metrics

@app.get("/api/leads")
def get_leads(limit: int = 100, offset: int = 0, status: str = None):
    """Get leads list with optional filter"""
    with SessionLocal() as session:
        from database.models import Lead, LeadStatus
        query = session.query(Lead)
        if status:
            query = query.filter(Lead.status == LeadStatus(status))
        leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": l.id,
                "address": l.address,
                "city": l.city,
                "price": l.price,
                "platform": l.platform.value if l.platform else None,
                "agent_email": l.agent_email,
                "agent_phone": l.agent_phone,
                "status": l.status.value if l.status else None,
                "email_opened": l.email_opened,
                "converted": l.converted_to_full_video,
                "created_at": l.created_at.isoformat() if l.created_at else None
            }
            for l in leads
        ]

@app.post("/api/scrape")
async def scrape_url(url: str, platform: str):
    """Manually trigger scrape for a single URL"""
    from scraper import get_scraper
    scraper = get_scraper(platform)
    data = scraper.scrape_listing(url)
    if data:
        return {"success": True, "data": data}
    else:
        raise HTTPException(status_code=400, detail="Scraping failed")

@app.post("/api/generate-video")
async def generate_video(listing_url: str, video_type: str = "teaser"):
    """Manually generate video for a listing (requires existing lead)"""
    from video.generator import VideoGenerator
    import json
    
    with SessionLocal() as session:
        lead = session.query(Lead).filter_by(listing_url=listing_url).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        gen = VideoGenerator(
            logo_path=settings.LOGO_PATH,
            music_dir=settings.MUSIC_DIR,
            output_dir=settings.VIDEO_OUTPUT_DIR
        )
        
        if video_type == "teaser":
            path = gen.generate_teaser(
                listing_data={
                    "price": lead.price,
                    "address": lead.address,
                    "beds": lead.beds,
                    "baths": lead.baths,
                    "sqft": lead.sqft
                },
                photo_urls=lead.photo_urls or []
            )
        else:
            path = gen.generate_full(
                listing_data={
                    "price": lead.price,
                    "address": lead.address,
                    "beds": lead.beds,
                    "baths": lead.baths,
                    "sqft": lead.sqft
                },
                photo_urls=lead.photo_urls or []
            )
        
        return {"success": True, "path": path}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.DASHBOARD_PORT)