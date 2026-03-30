"""Public-facing routes for landing pages, upsell, and delivery."""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from jinja2 import Template
from datetime import datetime
from typing import Optional

from app.utils.db import SessionLocal
from app.models.models import Lead, LandingPage, LandingPageSubmission, Order
from app.services.landing_service import LandingPageService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Jinja2 templates setup
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="app/templates/public")

landing_service = LandingPageService()

@router.get("/p/{slug}", response_class=HTMLResponse)
def serve_landing_page(request: Request, slug: str, db: Session = Depends(get_db)):
    """Serve personalized landing page with teaser video"""
    try:
        page = db.query(LandingPage).filter_by(slug=slug, status="active").first()
        if not page:
            raise HTTPException(status_code=404, detail="Landing page not found")
    except Exception as e:
        logger.error(f"Landing page error for slug {slug}: {e}")
        raise HTTPException(status_code=500, detail="Server error")
    
    # Ensure teaser video URL is available
    video_url = page.teaser_video_url
    # If stored as local path, serve via /videos/ prefix? For simplicity assume fully qualified URL
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "headline": page.headline,
        "subheadline": page.subheadline or "View your custom teaser video",
        "teaser_video_url": video_url,
        "landing_page_id": page.id,
        "year": datetime.utcnow().year
    })

@router.post("/api/submit-lead")
def submit_lead(
    request: Request,
    landing_page_id: int = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None)
):
    """Capture agent info from landing page"""
    db: Session = next(get_db())
    try:
        page = db.query(LandingPage).filter_by(id=landing_page_id).first()
        if not page:
            raise HTTPException(status_code=404, detail="Landing page not found")
        
        # Capture IP and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        submission = LandingPageSubmission(
            landing_page_id=landing_page_id,
            lead_id=page.lead_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        
        return JSONResponse(content={"success": True, "submission_id": submission.id})
    finally:
        db.close()

from app.core.config import settings
...
@router.get("/upsell", response_class=HTMLResponse)
def upsell_page(submission_id: int, request: Request, db: Session = Depends(get_db)):
    """Show premium upsell page after lead capture"""
    sub = db.query(LandingPageSubmission).filter_by(id=submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    lead = db.query(Lead).filter_by(id=sub.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    address = lead.address
    price = 250
    lead_id = lead.id
    return templates.TemplateResponse("upsell.html", {
        "request": request,
        "submission_id": submission_id,
        "address": address or "your listing",
        "price": price,
        "lead_id": lead_id,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "year": datetime.utcnow().year
    })

@router.get("/order/success", response_class=HTMLResponse)
def order_success(request: Request, session_id: str = None):
    """Stripe checkout success redirect"""
    # Could verify session with Stripe API if needed, but for now just show message
    return templates.TemplateResponse("success.html", {"request": request, "session_id": session_id, "year": datetime.utcnow().year})

@router.get("/order/cancel", response_class=HTMLResponse)
def order_cancel(request: Request):
    """Stripe checkout cancel redirect"""
    return templates.TemplateResponse("cancel.html", {"request": request, "year": datetime.utcnow().year})
