"""Scraping service with multi-platform support using Playwright and Zillow login"""
import os
import re
import time
import json
import logging
import random
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright
from app.core.config import settings
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ListingScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.cookies_file = os.path.join(settings.VIDEO_OUTPUT_DIR, "..", ".zillow_cookies.json")
        self.credentials = self._load_credentials()

    def _load_credentials(self) -> Optional[Dict]:
        cred_path = os.path.expanduser("~/.openclaw/credentials/web-credentials.json")
        if not os.path.exists(cred_path):
            logger.warning("No web credentials found; Zillow login disabled")
            return None
        try:
            with open(cred_path, 'r') as f:
                data = json.load(f)
            zillow = data.get('sites', {}).get('zillow')
            if not zillow:
                logger.warning("No Zillow credentials in web-credentials.json")
                return None
            return zillow
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None

    def _init_browser(self):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = self.context.new_page()
        self._ensure_logged_in()

    def _ensure_logged_in(self):
        if not self.credentials:
            logger.info("No credentials; proceeding without login")
            return
        # Try loading cookies if exist
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                self.context.add_cookies(cookies)
                logger.info("Loaded Zillow cookies from file")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        # Verify login by checking for account page or sign out
        try:
            self.page.goto("https://www.zillow.com/my/", timeout=30000)
            time.sleep(2)
            # If redirected to login, we need to log in
            if "login" in self.page.url.lower():
                logger.info("Not logged in; performing Zillow login")
                self._perform_login()
            else:
                logger.info("Zillow login verified")
        except Exception as e:
            logger.warning(f"Login check failed: {e}")

    def _perform_login(self):
        username = self.credentials.get('username')
        password = self.credentials.get('password')
        if not username or not password:
            logger.error("Missing Zillow credentials")
            return
        try:
            self.page.goto("https://www.zillow.com/user/login.htm", timeout=30000)
            time.sleep(2)
            # Fill email
            self.page.fill('input[name="username"]', username)
            # Fill password
            self.page.fill('input[name="password"]', password)
            # Click sign in
            self.page.click('button[type="submit"]')
            time.sleep(5)
            # Save cookies
            cookies = self.page.context.cookies()
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info("Zillow login successful; cookies saved")
        except Exception as e:
            logger.error(f"Zillow login failed: {e}")

    def _close_browser(self):
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
        except:
            pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def _random_delay(self):
        time.sleep(random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX))

    def fetch_listing_urls(self, search_url: str, limit: int = 50) -> List[str]:
        """Get listing URLs from a Zillow search results page using Playwright."""
        self._init_browser()
        try:
            self.page.goto(search_url, timeout=60000)
            self._random_delay()
            self.page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(2)
            links = []
            anchors = self.page.locator("a[href*='/homedetails/']").all()
            for a in anchors[:limit]:
                href = a.get_attribute("href")
                if href and href.startswith("http"):
                    if href not in links:
                        links.append(href)
                    if len(links) >= limit:
                        break
            return links[:limit]
        finally:
            self._close_browser()

    def scrape(self, url: str, platform: str) -> Dict[str, Any]:
        platform = platform.lower()
        if platform == "zillow":
            return self._scrape_zillow(url)
        elif platform == "redfin":
            return self._scrape_redfin(url)
        elif platform == "realtor_com":
            return self._scrape_realtor_com(url)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def _scrape_zillow(self, url: str) -> Dict[str, Any]:
        self._init_browser()
        try:
            self.page.goto(url, timeout=60000)
            self._random_delay()
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Price
            price = None
            price_el = soup.select_one('[data-testid="price"] span')
            if price_el:
                price_text = price_el.get_text(strip=True).replace("$", "").replace(",", "")
                try:
                    price = float(price_text)
                except:
                    price = None
            
            # Address
            address_el = soup.select_one("[data-testid='address']")
            address = address_el.get_text(strip=True) if address_el else ""
            
            # Beds/Baths/Sqft from facts
            beds = baths = sqft = None
            facts_els = soup.select('[data-testid="facts-list"] li')
            for fact in facts_els:
                text = fact.get_text(strip=True).lower()
                if "bd" in text:
                    try:
                        beds = float(re.search(r"[\d\.]+", text).group())
                    except: pass
                if "ba" in text:
                    try:
                        baths = float(re.search(r"[\d\.]+", text).group())
                    except: pass
                if "sqft" in text:
                    try:
                        sqft = int(re.search(r"[\d,]+", text).group().replace(",", ""))
                    except: pass
            
            # Photo URLs
            photo_urls = []
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and "image" in data:
                        img = data["image"]
                        if isinstance(img, list):
                            photo_urls.extend(img)
                        elif isinstance(img, str):
                            photo_urls.append(img)
                except:
                    pass
            if len(photo_urls) < 5:
                for img in soup.find_all("img", src=True):
                    src = img["src"]
                    if "zpid" in src or "photo" in src:
                        src = src.replace("\\", "")
                        photo_urls.append(src)
                photo_urls = list(dict.fromkeys(photo_urls))[:10]
            
            # Agent info: try page first, then click "Show contact info" if needed
            agent_name = agent_email = agent_phone = None
            
            # Try extracting from page directly
            agent_div = soup.find("div", class_=re.compile(r"agent", re.I))
            if agent_div:
                name_el = agent_div.find(["span", "p", "h3", "h4"], class_=re.compile(r"name", re.I))
                if name_el:
                    agent_name = name_el.get_text(strip=True)
                phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", agent_div.get_text())
                if phone_match:
                    agent_phone = phone_match.group()
                email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", agent_div.get_text())
                if email_match:
                    agent_email = email_match.group()
            
            # If email missing, try mailto
            if not agent_email:
                mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
                if mailto:
                    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
                    if email_match:
                        agent_email = email_match.group(0)
            
            # If still missing, try clicking "Show contact info" button via Playwright
            if not agent_email or not agent_name:
                try:
                    # Look for a button/link with text containing "Show contact" or "Contact agent"
                    contact_btn = self.page.locator("button:has-text('Show contact'), a:has-text('Show contact'), button:has-text('Contact agent'), a:has-text('Contact agent')").first
                    if contact_btn and contact_btn.is_visible():
                        contact_btn.click()
                        time.sleep(2)
                        # Grab updated DOM
                        updated_html = self.page.content()
                        soup = BeautifulSoup(updated_html, 'html.parser')
                        # Retry extraction
                        agent_div = soup.find("div", class_=re.compile(r"agent|contact", re.I))
                        if agent_div:
                            name_el = agent_div.find(["span", "p", "h3", "h4"], class_=re.compile(r"name", re.I))
                            if name_el:
                                agent_name = name_el.get_text(strip=True)
                            phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", agent_div.get_text())
                            if phone_match:
                                agent_phone = phone_match.group()
                            email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", agent_div.get_text())
                            if email_match:
                                agent_email = email_match.group()
                        # Also look for mailto in updated page
                        if not agent_email:
                            mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
                            if mailto:
                                email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
                                if email_match:
                                    agent_email = email_match.group(0)
                except Exception as e:
                    logger.warning(f"Contact button click failed: {e}")
            
            # Parse address into city/state/zip if possible
            city = state = zip_code = None
            if address:
                m = re.search(r",\s*([A-Za-z\s]+?),\s*([A-Z]{2})\s+(\d{5})", address)
                if m:
                    city = m.group(1).strip()
                    state = m.group(2)
                    zip_code = m.group(3)
            
            return {
                "listing_url": url,
                "platform": "zillow",
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
        finally:
            self._close_browser()

    def _scrape_redfin(self, url: str) -> Dict[str, Any]:
        raise NotImplementedError("Redfin scraping not yet implemented")

    def _scrape_realtor_com(self, url: str) -> Dict[str, Any]:
        raise NotImplementedError("Realtor.com scraping not yet implemented")

# Singleton
scraper = ListingScraper()

def run_scrape_for_all_sources(limit_per_source: int = 50) -> int:
    """Simple scraper: run Zillow search on a few city/state combos and ingest leads.
    Returns total new leads added.
    """
    from app.utils.db import SessionLocal
    from app.models.models import Lead, LeadStatus
    import re
    from bs4 import BeautifulSoup

    # Example search URLs (recent listings, high value)
    search_urls = [
        "https://www.zillow.com/homes/for_sale/New-York-NY/price-1000000-5000000/",
        "https://www.zillow.com/homes/for_sale/Los-Angeles-CA/price-1000000-5000000/",
        "https://www.zillow.com/homes/for_sale/Miami-FL/price-1000000-5000000/",
        "https://www.zillow.com/homes/for_sale/Chicago-IL/price-1000000-5000000/",
    ]
    total_new = 0
    db = SessionLocal()
    # Initialize browser once
    browser_initialized = False
    try:
        for url in search_urls:
            try:
                # Fetch search page HTML using Playwright via scraper's internal browser
                if not browser_initialized:
                    scraper._init_browser()
                    browser_initialized = True
                page = scraper.page
                page.goto(url, timeout=60000)
                page.wait_for_selector("div[data-testid='result-list']", timeout=30000)
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if re.search(r'/homedetails/', href) and 'zpid' in href:
                        full = href if href.startswith('http') else f"https://www.zillow.com{href}"
                        links.append(full)
                links = list(dict.fromkeys(links))[:limit_per_source]
                for listing_url in links:
                    try:
                        data = scraper._scrape_zillow(listing_url)
                        exists = db.query(Lead).filter_by(listing_url=listing_url).first()
                        if exists:
                            continue
                        lead = Lead(
                            listing_url=listing_url,
                            platform='zillow',
                            address=data.get('address'),
                            price=data.get('price'),
                            beds=data.get('beds'),
                            baths=data.get('baths'),
                            sqft=data.get('sqft'),
                            photo_urls=data.get('photo_urls', []),
                            agent_name=data.get('agent_name'),
                            agent_email=data.get('agent_email'),
                            agent_phone=data.get('agent_phone'),
                            city=data.get('city'),
                            state=data.get('state'),
                            zip_code=data.get('zip_code'),
                            status=LeadStatus.SCRAPED.value,
                        )
                        db.add(lead)
                        total_new += 1
                    except Exception as e:
                        logger.warning(f"Failed to scrape listing {listing_url}: {e}")
                db.commit()
            except Exception as e:
                logger.error(f"Error processing search URL {url}: {e}")
        return total_new
    finally:
        if browser_initialized:
            scraper._close_browser()
        db.close()

def run_scrape_for_all_sources(limit_per_source: int = 50) -> int:
    """Simple scraper: run Zillow search on a few city/state combos and ingest leads.
    Returns total new leads added.
    """
    from app.utils.db import SessionLocal
    from app.models.models import Lead, LeadStatus
    import re
    from bs4 import BeautifulSoup

    # Example search URLs (recent listings, high value)
    search_urls = [
        "https://www.zillow.com/homes/for_sale/New-York-NY/price-1000000-5000000/",
        "https://www.zillow.com/homes/for_sale/Los-Angeles-CA/price-1000000-5000000/",
        "https://www.zillow.com/homes/for_sale/Miami-FL/price-1000000-5000000/",
        "https://www.zillow.com/homes/for_sale/Chicago-IL/price-1000000-5000000/",
    ]
    total_new = 0
    db = SessionLocal()
    browser_initialized = False
    try:
        for url in search_urls:
            try:
                if not browser_initialized:
                    scraper._init_browser()
                    browser_initialized = True
                page = scraper.page
                page.goto(url, timeout=60000)
                page.wait_for_selector("div[data-testid='result-list']", timeout=30000)
                html = page.content()
                # Extract listing URLs from search results
                soup = BeautifulSoup(html, 'html.parser')
                links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if re.search(r'/homedetails/', href) and 'zpid' in href:
                        full = href if href.startswith('http') else f"https://www.zillow.com{href}"
                        links.append(full)
                links = list(dict.fromkeys(links))[:limit_per_source]
                for listing_url in links:
                    try:
                        data = scraper._scrape_zillow(listing_url)
                        # Check if exists
                        exists = db.query(Lead).filter_by(listing_url=listing_url).first()
                        if exists:
                            continue
                        lead = Lead(
                            listing_url=listing_url,
                            platform='zillow',
                            address=data.get('address'),
                            price=data.get('price'),
                            beds=data.get('beds'),
                            baths=data.get('baths'),
                            sqft=data.get('sqft'),
                            photo_urls=data.get('photo_urls', []),
                            agent_name=data.get('agent_name'),
                            agent_email=data.get('agent_email'),
                            agent_phone=data.get('agent_phone'),
                            city=data.get('city'),
                            state=data.get('state'),
                            zip_code=data.get('zip_code'),
                            status=LeadStatus.SCRAPED.value,
                        )
                        db.add(lead)
                        total_new += 1
                    except Exception as e:
                        logger.warning(f"Failed to scrape listing {listing_url}: {e}")
                db.commit()
            except Exception as e:
                logger.error(f"Error processing search URL {url}: {e}")
        return total_new
    finally:
        if browser_initialized:
            scraper._close_browser()
        db.close()