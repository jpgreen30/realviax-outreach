"""Additional scrapers for Realtor.com and Redfin (contact info often visible)"""
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional

class RealtorComScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def _random_delay(self):
        time.sleep(random.uniform(1, 3))

    def fetch_listing_urls(self, search_url: str, limit: int = 50) -> List[str]:
        self._random_delay()
        resp = self.session.get(search_url, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Realtor.com search failed: HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/realestate/' in href and href.startswith('http'):
                if href not in links:
                    links.append(href)
                if len(links) >= limit:
                    break
        return links[:limit]

    def scrape(self, url: str) -> Dict[str, Any]:
        self._random_delay()
        resp = self.session.get(url, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Realtor.com fetch failed: HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Price
        price = None
        price_el = soup.select_one('[data-label="price"]')
        if price_el:
            price_text = price_el.get_text(strip=True).replace("$", "").replace(",", "")
            try:
                price = float(price_text)
            except:
                price = None

        # Address
        address_el = soup.select_one('[data-label="address"]')
        address = address_el.get_text(strip=True) if address_el else ""

        # Beds/Baths/Sqft
        beds = baths = sqft = None
        bed_el = soup.select_one('[data-label="beds"]')
        if bed_el:
            try:
                beds = float(re.search(r"[\d\.]+", bed_el.get_text()).group())
            except: pass
        bath_el = soup.select_one('[data-label="baths"]')
        if bath_el:
            try:
                baths = float(re.search(r"[\d\.]+", bath_el.get_text()).group())
            except: pass
        sqft_el = soup.select_one('[data-label="sqft"]')
        if sqft_el:
            try:
                sqft = int(re.search(r"[\d,]+", sqft_el.get_text()).group().replace(",", ""))
            except: pass

        # Photos: look for large image URLs
        photo_urls = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if "realtor.com" in src and ("photo" in src or "image" in src):
                photo_urls.append(src)
        photo_urls = list(dict.fromkeys(photo_urls))[:10]

        # Agent info: often in a "listing-agent" section
        agent_name = agent_email = agent_phone = None
        agent_section = soup.find("div", class_=re.compile(r"listing-agent|agent-contact", re.I))
        if agent_section:
            name_el = agent_section.find(["span", "p", "h3"], class_=re.compile(r"name", re.I))
            if name_el:
                agent_name = name_el.get_text(strip=True)
            phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", agent_section.get_text())
            if phone_match:
                agent_phone = phone_match.group()
            email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", agent_section.get_text())
            if email_match:
                agent_email = email_match.group()

        # Also look for mailto
        if not agent_email:
            mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
            if mailto:
                email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
                if email_match:
                    agent_email = email_match.group(0)

        # Parse city/state/zip from address
        city = state = zip_code = None
        if address:
            m = re.search(r",\s*([A-Za-z\s]+?),\s*([A-Z]{2})\s+(\d{5})", address)
            if m:
                city = m.group(1).strip()
                state = m.group(2)
                zip_code = m.group(3)

        return {
            "listing_url": url,
            "platform": "realtor_com",
            "address": address,
            "price": price,
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "photo_urls": photo_urls,
            "agent_name": agent_name,
            "agent_email": agent_email,
            "agent_phone": agent_phone,
            "property_type": None,
            "city": city,
            "state": state,
            "zip_code": zip_code,
        }

# Singleton for potential use
realtor_scraper = RealtorComScraper()