#!/usr/bin/env python3
"""Scrape agent leads from Realtor.com and Keller Williams."""
import sys
sys.path.insert(0, '/home/jpgreen1/.openclaw/workspace/realviax-outreach')
import asyncio
from app.services.lead_sources.realtor_agents import RealtorAgentsScraper
from app.services.lead_sources.kw_agents import KWAgentsScraper
from app.utils.db import SessionLocal
from app.models.models import Lead, LeadStatus
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_and_ingest(source_name, scraper, city, state, limit=50):
    db = SessionLocal()
    try:
        leads_data = await scraper.scrape({"city": city, "state": state, "limit": limit})
        new_count = 0
        for data in leads_data:
            agent_email = data.get('agent_email')
            if not agent_email:
                continue
            # Determine unique field
            if source_name == 'realtor_agents':
                unique_field = 'listing_url'
                unique_value = data.get('listing_url')
            else:
                unique_field = 'listing_url'  # KW scraper returns listing_url from their active listings? Let's check.
                unique_value = data.get('listing_url') or data.get('profile_url')
            if not unique_value:
                continue
            exists = db.query(Lead).filter_by(**{unique_field: unique_value}).first()
            if exists:
                continue
            lead = Lead(
                listing_url=unique_value,
                platform='realtor_com' if source_name == 'realtor_agents' else 'keller_williams',
                agent_name=data.get('agent_name'),
                agent_email=agent_email,
                agent_phone=data.get('agent_phone'),
                office_name=data.get('office_name') or data.get('team_name'),
                city=data.get('city'),
                state=data.get('state'),
                zip_code=data.get('zip_code'),
                status=LeadStatus.SCRAPED.value,
            )
            db.add(lead)
            new_count += 1
            logger.info(f"Added {source_name} lead: {agent_email} – {unique_value}")
        db.commit()
        logger.info(f"{source_name}: added {new_count} new leads")
        return new_count
    finally:
        db.close()

async def main():
    total = 0
    # Realtor.com agents: Los Angeles
    realtor_scraper = RealtorAgentsScraper()
    total += await scrape_and_ingest('realtor_agents', realtor_scraper, 'Los Angeles', 'CA', limit=50)
    # Keller Williams agents: Miami
    kw_scraper = KWAgentsScraper()
    total += await scrape_and_ingest('kw_agents', kw_scraper, 'Miami', 'FL', limit=50)
    print(f"Total new agent leads added: {total}")

if __name__ == "__main__":
    asyncio.run(main())
