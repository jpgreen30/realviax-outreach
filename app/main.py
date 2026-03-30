"""Realviax Outreach - Autonomous lead generation and outreach system"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
from app.core.config import settings
from app.utils.db import engine
from app.models.models import Base
from app.routers import leads, health, video, auth, payments, webhooks, admin, monitor, scraper

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Realviax Outreach API",
    description="Autonomous lead scraping, video generation, and email outreach",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for videos
import os
VIDEO_DIR = settings.VIDEO_OUTPUT_DIR
if os.path.exists(VIDEO_DIR):
    app.mount("/videos", StaticFiles(directory=VIDEO_DIR), name="videos")

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(video.router, prefix="/api/v1/video", tags=["video"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(monitor.router, prefix="/api", tags=["monitor"])
app.include_router(scraper.router, prefix="/api", tags=["scraper"])

@app.get("/")
def root():
    return {"status": "ok", "service": "Realviax Outreach", "timestamp": datetime.utcnow().isoformat()}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logging.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": str(exc)})