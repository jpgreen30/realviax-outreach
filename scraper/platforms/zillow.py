"""
Zillow listing scraper
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from .extractors import ListingExtractor
from ..anti_detection import StealthWrapper
import logging

logger = logging.getLogger(__name__)

class ZillowScraper:
    BASE_URL = "https://www.zillow.com"
    
    def __init__(self, use_stealth: bool = True):
        self.use_stealth = use_stealth
        self.session = requests.Session()
    
    def scrape_listing(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single listing page"""
        try:
            # Get page
            headers = StealthWrapper.get_random_headers() if self.use_stealth else {}
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data
            extractor = ListingExtractor()
            address_data = extractor.extract_address(soup)
            
            # Get price
            price = extractor.extract_price(soup.get_text())
            
            # Get beds/baths/sqft
            beds_baths_sqft = extractor.extract_beds_baths_sqft(soup.get_text())
            
            # Get agent info
            agent_info = extractor.extract_agent_info(soup)
            
            # Get photos
            photos = extractor.extract_photo_urls(soup, self.BASE_URL)
            # Filter to main property photos (usually larger)
            photos = [p for p in photos if 'zillow' in p.lower()][:20]  # Limit to 20
            
            # Build result
            result = {
                "platform": "zillow",
                "listing_url": url,
                **address_data,
                "price": price,
                **beds_baths_sqft,
                **agent_info,
                "photo_urls": photos,
                "raw_html_length": len(response.text)
            }
            
            logger.info(f"Scraped Zillow listing: {address_data.get('address')}")
            return result
            
        except Exception as e:
            logger.error(f"Zillow scrape failed for {url}: {e}")
            return None
    
    def search_listings(self, search_url: str, max_results: int = 10) -> list:
        """Scrape search results page to get listing URLs"""
        results = []
        try:
            headers = StealthWrapper.get_random_headers() if self.use_stealth else {}
            response = self.session.get(search_url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Zillow listing links contain '/homedetails/'
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if '/homedetails/' in href and href not in results:
                    if not href.startswith('http'):
                        href = self.BASE_URL + href
                    results.append(href)
                    if len(results) >= max_results:
                        break
            return results
        except Exception as e:
            logger.error(f"Zillow search failed: {e}")
            return []