"""
Extract listing data from scraped HTML
"""
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class ListingExtractor:
    """Extract structured listing data from HTML"""
    
    @staticmethod
    def extract_price(html_text: str) -> Optional[float]:
        """Extract price from HTML/text"""
        # Matches: $750,000 or 750000
        matches = re.findall(r'\$?([\d,]+)', html_text)
        for match in matches:
            # Look for a number with at least 5 digits (typical home price)
            num = int(match.replace(',', ''))
            if num >= 100000:  # reasonable home price
                return float(num)
        return None
    
    @staticmethod
    def extract_beds_baths_sqft(html_text: str) -> Dict[str, Optional[float]]:
        """Extract beds, baths, sqft from text"""
        result = {"beds": None, "baths": None, "sqft": None}
        
        # Beds: "3 beds" or "3 bed"
        beds_match = re.search(r'(\d+(?:\.\d+)?)\s+bed', html_text, re.IGNORECASE)
        if beds_match:
            result["beds"] = float(beds_match.group(1))
        
        # Baths: "2 baths" or "2 bath"
        baths_match = re.search(r'(\d+(?:\.\d+)?)\s+bath', html_text, re.IGNORECASE)
        if baths_match:
            result["baths"] = float(baths_match.group(1))
        
        # Sqft: "2,500 sqft" or "2500 sq. ft."
        sqft_match = re.search(r'([\d,]+)\s+sq(?:\.?\s*ft)?', html_text, re.IGNORECASE)
        if sqft_match:
            result["sqft"] = int(sqft_match.group(1).replace(',', ''))
        
        return result
    
    @staticmethod
    def extract_address(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract address components"""
        result = {"address": None, "city": None, "state": None, "zip": None}
        
        # Try common selectors
        address_elem = soup.find('h1') or soup.find('h2')
        if address_elem:
            result["address"] = address_elem.get_text(strip=True)
        
        # Look for structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if data.get("@type") == "Place" or data.get("@type") == "Residence":
                        addr = data.get("address", {})
                        result.update({
                            "address": addr.get("streetAddress"),
                            "city": addr.get("addressLocality"),
                            "state": addr.get("addressRegion"),
                            "zip": addr.get("postalCode")
                        })
            except:
                pass
        
        return result
    
    @staticmethod
    def extract_agent_info(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract agent contact info"""
        result = {"agent_name": None, "agent_phone": None, "agent_email": None, "office_name": None}
        
        # Look for email addresses
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(soup))
        if emails:
            # Filter out generic emails (info@, noreply@)
            for email in emails:
                if not any(prefix in email.lower() for prefix in ['info@', 'noreply@', 'webmaster@']):
                    result["agent_email"] = email
                    break
        
        # Look for phone numbers
        phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', str(soup))
        if phones:
            result["agent_phone"] = phones[0]
        
        # Agent name often in specific tags
        agent_elem = soup.find('span', class_=re.compile(r'agent|broker|realtor', re.I))
        if agent_elem:
            result["agent_name"] = agent_elem.get_text(strip=True)
        
        return result
    
    @staticmethod
    def extract_photo_urls(soup: BeautifulSoup, base_url: str) -> list:
        """Extract all property image URLs"""
        photos = []
        imgs = soup.find_all('img')
        for img in imgs:
            src = img.get('src') or img.get('data-src')
            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                # Convert relative URLs
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = base_url.rstrip('/') + src
                photos.append(src)
        return list(set(photos))  # Deduplicate