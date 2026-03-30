"""
Redfin listing scraper
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from .extractors import ListingExtractor
from ..anti_detection import StealthWrapper
import logging

logger = logging.getLogger(__name__)

class RedfinScraper:
    BASE_URL = "https://www.redfin.com"
    
    def __init__(self, use_stealth: bool = True):
        self.use_stealth = use_stealth
        self.session = requests.Session()
    
    def scrape_listing(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            headers = StealthWrapper.get_random_headers() if self.use_stealth else {}
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            extractor = ListingExtractor()
            
            address_data = extractor.extract_address(soup)
            price = extractor.extract_price(soup.get_text())
            beds_baths_sqft = extractor.extract_beds_baths_sqft(soup.get_text())
            agent_info = extractor.extract_agent_info(soup)
            photos = extractor.extract_photo_urls(soup, self.BASE_URL)
            photos = [p for p in photos if 'redfin' in p.lower()][:20]
            
            result = {
                "platform": "redfin",
                "listing_url": url,
                **address_data,
                "price": price,
                **beds_baths_sqft,
                **agent_info,
                "photo_urls": photos,
                "raw_html_length": len(response.text)
            }
            
            logger.info(f"Scraped Redfin listing: {address_data.get('address')}")
            return result
            
        except Exception as e:
            logger.error(f"Redfin scrape failed for {url}: {e}")
            return None
    
    def search_listings(self, search_url: str, max_results: int = 10) -> list:
        results = []
        try:
            headers = StealthWrapper.get_random_headers() if self.use_stealth else {}
            response = self.session.get(search_url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if '/home/' in href and href not in results:
                    if not href.startswith('http'):
                        href = self.BASE_URL + href
                    results.append(href)
                    if len(results) >= max_results:
                        break
            return results
        except Exception as e:
            logger.error(f"Redfin search failed: {e}")
            return []