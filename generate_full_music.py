#!/usr/bin/env python3
import sys
import logging
sys.path.insert(0, '/home/jpgreen1/.openclaw/workspace/realviax-outreach')

from app.services.video_generator import VideoGenerator
from app.core.config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create generator
video_gen = VideoGenerator(
    logo_path=settings.LOGO_PATH,
    music_dir=settings.MUSIC_DIR,
    output_dir=settings.VIDEO_OUTPUT_DIR
)

# Dummy test lead
lead_id = 1
photo_urls = [
    "https://images.unsplash.com/photo-1512918760513-95f6922c8d62?w=1080",
    "https://images.unsplash.com/photo-1564013799919-ab600587ffc6?w=1080",
    "https://images.unsplash.com/photo-1584622658111-993a426fbf0a?w=1080",
    "https://images.unsplash.com/photo-1500813347199-6d229a477b44?w=1080",
    "https://images.unsplash.com/photo-1512918760513-95f6922c8d62?w=1080",
    "https://images.unsplash.com/photo-1564013799919-ab600587ffc6?w=1080",
    "https://images.unsplash.com/photo-1584622658111-993a426fbf0a?w=1080",
    "https://images.unsplash.com/photo-1500813347199-6d229a477b44?w=1080",
]
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
