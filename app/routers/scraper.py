"""Scraper configuration endpoints."""
from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus
from app.services.lead_sources.realtor_agents import RealtorAgentsScraper
from app.services.lead_sources.kw_agents import KWAgentsScraper

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/scrape-leads")
async def scrape_leads(config: Dict[str, Any] = Body(...)):
    """
    Scrape real estate agent leads from configured source.
    Expected config:
    {
        "source": "realtor_agents" or "kw_agents",
        "city": "City Name",
        "state": "ST",
        "limit": 50 (optional)
    }
    Returns number of new leads created.
    """
    source = config.get("source")
    if source not in ("realtor_agents", "kw_agents"):
        raise HTTPException(status_code=400, detail=f"Unsupported source: {source}")

    city = config.get("city")
    state = config.get("state")
    if not city or not state:
        raise HTTPException(status_code=400, detail="city and state are required")

    limit = config.get("limit", 50)
    proxy = config.get("proxy")  # Optional proxy URL

    if source == "realtor_agents":
        scraper = RealtorAgentsScraper(proxy=proxy)
    else:
        scraper = KWAgentsScraper(proxy=proxy)

    try:
        leads_data = await scraper.scrape({"city": city, "state": state, "limit": limit})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

    new_count = 0
    db: Session = next(get_db())
    try:
        for data in leads_data:
            logger.info(f"Processing lead data: {data}")
            # Ensure required agent_email
            agent_email = data.get('agent_email')
            if not agent_email:
                logger.warning("Skipping lead due to missing agent_email")
                continue
            # Determine unique key: for realtors use listing_url, for kw use profile_url
            unique_field = 'listing_url' if source == 'realtor_agents' else 'profile_url'
            unique_value = data.get(unique_field)
            if not unique_value:
                continue
            existing = db.query(Lead).filter_by(**{unique_field: unique_value}).first()
            if existing:
                continue
            lead = Lead(
                listing_url=unique_value,
                platform='realtor_com' if source == 'realtor_agents' else 'keller_williams',
                agent_name=data.get("agent_name"),
                agent_email=agent_email,
                agent_phone=data.get("agent_phone"),
                office_name=data.get("office_name") or data.get("team_name"),
                city=data.get("city"),
                state=data.get("state"),
                zip_code=data.get("zip_code"),
                status=LeadStatus.SCRAPED.value,
            )
            db.add(lead)
            new_count += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        db.close()

    return {
        "source": source,
        "city": city,
        "state": state,
        "new_leads": new_count,
        "processed": len(leads_data)
    }