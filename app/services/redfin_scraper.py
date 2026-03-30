"""Redfin scraper — contact info typically visible without login"""
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional

class RedfinScraper:
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
            raise RuntimeError(f"Redfin search failed: HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/redfin.com/' in href and '/home/' in href and href.startswith('http'):
                if href not in links:
                    links.append(href)
                if len(links) >= limit:
                    break
        return links[:limit]

    def scrape(self, url: str) -> Dict[str, Any]:
        self._random_delay()
        resp = self.session.get(url, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Redfin fetch failed: HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Price
        price = None
        price_el = soup.select_one('[data-rf-test-id="abp-price"]') or soup.select_one('.price')
        if price_el:
            price_text = price_el.get_text(strip=True).replace("$", "").replace(",", "")
            try:
                price = float(price_text)
            except:
                price = None

        # Address
        address_el = soup.select_one('[data-rf-test-id="abp-address"]') or soup.select_one('.address')
        address = address_el.get_text(strip=True) if address_el else ""

        # Beds/Baths/Sqft
        beds = baths = sqft = None
        stats_els = soup.select('[data-rf-test-id="abp-bed"]') or soup.select('.stats > .stat')
        for stat in stats_els:
            text = stat.get_text(strip=True).lower()
            if 'bd' in text or 'bed' in text:
                try:
                    beds = float(re.search(r"[\d\.]+", text).group())
                except: pass
            if 'ba' in text or 'bath' in text:
                try:
                    baths = float(re.search(r"[\d\.]+", text).group())
                except: pass
            if 'sqft' in text:
                try:
                    sqft = int(re.search(r"[\d,]+", text).group().replace(",", ""))
                except: pass

        # Photos
        photo_urls = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if "redfin.com" in src and ("photo" in src or "image" in src):
                photo_urls.append(src)
        photo_urls = list(dict.fromkeys(photo_urls))[:10]

        # Agent info: Redfin often shows broker/agent in a sidebar
        agent_name = agent_email = agent_phone = None
        agent_section = soup.find("div", class_=re.compile(r"agent|broker", re.I))
        if not agent_section:
            agent_section = soup.find("section", class_=re.compile(r"agent", re.I))
        if agent_section:
            name_el = agent_section.find(["span", "p", "h3", "h4"], class_=re.compile(r"name", re.I))
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

        # Parse city/state/zip
        city = state = zip_code = None
        if address:
            m = re.search(r",\s*([A-Za-z\s]+?),\s*([A-Z]{2})\s+(\d{5})", address)
            if m:
                city = m.group(1).strip()
                state = m.group(2)
                zip_code = m.group(3)

        return {
            "listing_url": url,
            "platform": "redfin",
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

# Singleton
redfin_scraper = RedfinScraper()