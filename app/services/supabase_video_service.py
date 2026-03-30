"""Supabase video storage service with local fallback"""
from pathlib import Path
from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseVideoService:
    def __init__(self):
        self.supabase = None
        self.bucket_name = settings.SUPABASE_BUCKET
        self._initialized = False
        
    def _ensure_client(self):
        if self._initialized:
            return
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning("Supabase not configured; video uploads will be skipped")
            self._initialized = True
            return
        try:
            self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            self._ensure_bucket()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            self.supabase = None
            self._initialized = True

    def _ensure_bucket(self):
        try:
            buckets = self.supabase.storage.list_buckets()
            if not any(b['name'] == self.bucket_name for b in buckets):
                self.supabase.storage.create_bucket(self.bucket_name, public=True)
                logger.info(f"Created Supabase storage bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to ensure bucket: {e}")

    def upload_video(self, local_path: str, lead_id: int, video_type: str = "teaser") -> str:
        self._ensure_client()
        if not self.supabase:
            logger.warning(f"Skipping upload (Supabase not configured): {local_path}")
            # Use a fallback URL that matches the expected local static file path
            # Actual files are named: lead_{lead_id}_{video_type}.mp4 inside VIDEO_OUTPUT_DIR
            return f"/videos/lead_{lead_id}_{video_type}.mp4"
        supabase_path = f"{lead_id}/{video_type}/{Path(local_path).name}"
        try:
            with open(local_path, 'rb') as f:
                self.supabase.storage.from_(self.bucket_name).upload(
                    supabase_path, f, file_options={"content-type": "video/mp4"}
                )
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(supabase_path)
            logger.info(f"Uploaded video to Supabase: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload video {local_path}: {e}")
            return f"/videos/lead_{lead_id}_{video_type}.mp4"

    def delete_lead_videos(self, lead_id: int):
        self._ensure_client()
        if not self.supabase:
            return
        try:
            response = self.supabase.storage.from_(self.bucket_name).list(f"{lead_id}/")
            paths = [f"{lead_id}/{item['name']}" for item in response]
            if paths:
                self.supabase.storage.from_(self.bucket_name).remove(paths)
                logger.info(f"Deleted {len(paths)} videos for lead {lead_id}")
        except Exception as e:
            logger.error(f"Failed to delete videos for lead {lead_id}: {e}")

# Singleton
supabase_video_service = SupabaseVideoService()
