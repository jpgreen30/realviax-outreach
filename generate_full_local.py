#!/usr/bin/env python3
import sys
import os
import logging
sys.path.insert(0, '/home/jpgreen1/.openclaw/workspace/realviax-outreach')

from app.services.video_generator import VideoGenerator
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create generator
video_gen = VideoGenerator(
    logo_path=settings.LOGO_PATH,
    music_dir=settings.MUSIC_DIR,
    output_dir=settings.VIDEO_OUTPUT_DIR
)

lead_id = 1
# Use local photos we have
photo_dir = '/home/jpgreen1/.openclaw/workspace/realviax-outreach/assets/photos'
photo_files = sorted([f for f in os.listdir(photo_dir) if f.endswith('.jpg')])
photo_urls = [f"file://{photo_dir}/{f}" for f in photo_files]
listing_data = {
    "address": "123 Luxury Ave, Beverly Hills, CA",
    "price": "$2,500,000",
    "beds": 5,
    "baths": 4,
    "sqft": 3500,
}

try:
    path = video_gen.generate_full(lead_id, photo_urls, listing_data)
    print(f"SUCCESS: {path}")
except Exception as e:
    logger.exception("Generation failed")
    print(f"FAILED: {e}")
    sys.exit(1)
