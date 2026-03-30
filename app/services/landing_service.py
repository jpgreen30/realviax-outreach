"""Landing page service: creates and serves personalized teaser pages."""
import os
import logging
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from jinja2 import Template

from app.models.models import LandingPage, Property, Lead, Order
from app.core.config import settings

logger = logging.getLogger(__name__)

class LandingPageService:
    """Create and serve personalized landing pages"""
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("APP_BASE_URL", "https://realviax.com")
        self.template_dir = Path(__file__).parent.parent / "templates" / "public"
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Load HTML template
        self.template_path = self.template_dir / "landing.html"
        if not self.template_path.exists():
            self._create_default_template()

        self.template = Template(self.template_path.read_text())

    def _create_default_template(self):
        """Create a basic landing page template"""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ headline }} | Realviax</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
  <div class="max-w-4xl mx-auto p-6">
    <h1 class="text-3xl font-bold mb-2">{{ headline }}</h1>
    <p class="text-gray-600 mb-6">{{ subheadline }}</p>
    <div class="bg-white rounded-lg shadow-lg p-4 mb-6">
      <video width="100%" controls muted autoplay loop playsinline>
        <source src="{{ teaser_video_url }}" type="video/mp4">
        Your browser does not support video playback. You can <a href="{{ teaser_video_url }}">download the video</a> instead.
      </video>
    </div>
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-semibold mb-4">Claim Your Free Teaser</h2>
      <form id="lead-form" action="/api/submit-lead" method="POST">
        <input type="hidden" name="landing_page_id" value="{{ landing_page_id }}">
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">First Name</label>
            <input type="text" name="first_name" required class="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
            <input type="text" name="last_name" required class="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" name="email" required class="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Phone</label>
            <input type="tel" name="phone" class="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500">
          </div>
        </div>
        <button type="submit" class="mt-4 bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition">Submit</button>
      </form>
    </div>
    <div class="mt-8 text-sm text-gray-500">
      <p>&copy; {{ year }} Realviax Studios. All rights reserved.</p>
      <p><a href="/privacy">Privacy Policy</a> | <a href="/terms">Terms of Service</a></p>
    </div>
  </div>
  <script>
    document.getElementById('lead-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      try {
        const resp = await fetch('/api/submit-lead', { method: 'POST', body: formData });
        if (resp.ok) {
          const data = await resp.json();
          window.location.href = '/upsell?submission_id=' + data.submission_id;
        } else {
          alert('Error submitting form');
        }
      } catch (err) {
        alert('Network error');
      }
    });
  </script>
</body>
</html>
"""
        self.template_path.write_text(html)

    def create_landing_page(self, db: Session, lead: Lead, teaser_video_url: str, thumbnail_url: Optional[str] = None) -> LandingPage:
        """Register a new personalized landing page or update existing"""
        # Ensure property exists; or create one from lead data
        prop = lead.property
        if not prop:
            prop = Property(
                lead_id=lead.id,
                listing_url=lead.listing_url,
                address=lead.address,
                city=lead.city,
                state=lead.state,
                zip_code=lead.zip_code,
                price=lead.price,
                beds=lead.beds,
                baths=lead.baths,
                sqft=lead.sqft,
            )
            db.add(prop)
            db.flush()
        else:
            # Ensure property_id is set; if prop exists but has no id? It does.
            pass

        # Check for existing landing page for this lead
        existing = db.query(LandingPage).filter_by(lead_id=lead.id).first()
        if existing:
            # Update existing page
            existing.teaser_video_url = teaser_video_url
            existing.property_id = prop.id
            if thumbnail_url:
                existing.thumbnail_url = thumbnail_url
            # Could update headline, etc.
            db.commit()
            logger.info(f"Updated existing landing page {existing.slug} for lead {lead.id}")
            return existing

        # Generate unique slug
        slug = f"lp-{secrets.token_urlsafe(8)}"

        page = LandingPage(
            lead_id=lead.id,
            property_id=prop.id,
            slug=slug,
            teaser_video_url=teaser_video_url,
            thumbnail_url=thumbnail_url,
            headline=f"Teaser Preview: {lead.address or 'Your Listing'}",
            subheadline="See what a cinematic video could look like for this property.",
            status="active"
        )
        db.add(page)
        db.commit()
        logger.info(f"Created landing page {slug} for lead {lead.id}")
        return page

    def get_context(self, db: Session, slug: str) -> Dict[str, Any]:
        """Get template context for a landing page"""
        page = db.query(LandingPage).filter_by(slug=slug, status="active").first()
        if not page:
            raise ValueError("Landing page not found or inactive")

        return {
            "headline": page.headline,
            "subheadline": page.headline,
            "teaser_video_url": page.teaser_video_url,
            "landing_page_id": page.id,
            "year": datetime.utcnow().year
        }

    def render_page(self, db: Session, slug: str) -> str:
        ctx = self.get_context(db, slug)
        return self.template.render(**ctx)
