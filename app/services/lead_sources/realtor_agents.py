"""Realtor.com agent directory scraper using Playwright async API."""
import logging
import re
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright
from .base import BaseLeadSource

logger = logging.getLogger(__name__)

class RealtorAgentsScraper(BaseLeadSource):
    """Async scraper for Realtor.com agent directory."""
    
    BASE_URL = "https://www.realtor.com/realestateagents"
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None, debug_dir: Optional[str] = None):
        super().__init__(headless=headless, proxy=proxy)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.debug_dir = debug_dir
    
    async def _start_browser(self):
        if self.page:
            return
        self.playwright = await async_playwright().start()
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
        if self.proxy:
            browser_args.append(f'--proxy-server={self.proxy}')
        self.browser = await self.playwright.chromium.launch(headless=self.headless, args=browser_args)
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1280, "height": 800},
            "locale": "en-US",
        }
        if self.proxy:
            context_options["proxy"] = {"server": self.proxy}
        self.context = await self.browser.new_context(**context_options)
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3] });
        """)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
    
    async def _close_browser(self):
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    def _random_delay(self, min_delay=2, max_delay=3):
        import random, time
        time.sleep(random.uniform(min_delay, max_delay))

    async def _save_debug_screenshot(self, name: str):
        if self.debug_dir and self.page:
            import os
            os.makedirs(self.debug_dir, exist_ok=True)
            path = os.path.join(self.debug_dir, f"{name}.png")
            await self.page.screenshot(path=path, full_page=True)
            logger.info(f"Saved screenshot: {path}")
    
    async def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape leads according to config and return normalized lead data dicts.
        Expected config: {city, state, limit}
        """
        city = config.get("city")
        state = config.get("state")
        limit = config.get("limit", 50)
        if not city or not state:
            raise ValueError("city and state are required")
        
        await self._start_browser()
        try:
            return await self.scrape_city(city, state, limit)
        finally:
            await self._close_browser()
    
    async def scrape_city(self, city: str, state: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape agents for a given city and state and return list of lead dicts."""
        leads: List[Dict[str, Any]] = []
        errors = []
        
        city_slug = city.lower().replace(' ', '-')
        state_code = state.upper()
        url = f"{self.BASE_URL}/{city_slug}_{state_code}"
        
        logger.info(f"Scraping agents from {url} (limit={limit})")
        
        try:
            await self.page.goto(url, timeout=60000)
            await self._random_delay()
            
            content = await self.page.content()
            if "Your request could not be processed" in content or "Access to this page has been denied" in content or "Please verify you are human" in content:
                logger.warning(f"Block page detected for {city}, {state}")
                await self._save_debug_screenshot(f"block_{city_slug}_{state_code}")
                raise RuntimeError(f"Blocked by Realtor.com for {city}, {state}")
            
            # Capture initial page for debugging
            await self._save_debug_screenshot(f"initial_{city_slug}_{state_code}")
            
            # Collect agent profile links
            agent_links = set()
            last_count = 0
            max_scrolls = 15
            for i in range(max_scrolls):
                anchors = await self.page.locator("a[href*='/realestateagents/']").all()
                for a in anchors:
                    href = await a.get_attribute("href")
                    if href and href.startswith("http"):
                        if f"/realestateagents/{city_slug}_{state_code}" not in href:
                            agent_links.add(href)
                if len(agent_links) >= limit:
                    break
                await self.page.evaluate("window.scrollBy(0, document.body.scrollHeight * 0.9)")
                await self._random_delay()
                if len(agent_links) == last_count:
                    load_more = self.page.locator("button:has-text('Load More'), button:has-text('Show More')").first
                    if await load_more.is_visible(timeout=1000):
                        await load_more.click()
                        await self._random_delay()
                    else:
                        break
                last_count = len(agent_links)
            
            agent_urls = list(agent_links)[:limit]
            total_found = len(agent_urls)
            logger.info(f"Found {total_found} agent profile URLs for {city}, {state}")
            
            for profile_url in agent_urls:
                try:
                    lead_data = await self._scrape_agent_profile(profile_url, city, state)
                    if lead_data:
                        leads.append(lead_data)
                except Exception as e:
                    errors.append(f"Error scraping {profile_url}: {str(e)}")
                    logger.exception(e)
                    
        except Exception as e:
            errors.append(f"Error scraping city {city}, {state}: {str(e)}")
            logger.exception(e)
        
        if errors:
            logger.warning(f"Completed with {len(errors)} errors for {city}, {state}")
        
        return leads
    
    async def _scrape_agent_profile(self, profile_url: str, city: str, state: str) -> Optional[Dict[str, Any]]:
        """Scrape individual agent profile and return normalized lead data dict."""
        await self.page.goto(profile_url, timeout=60000)
        await self._random_delay()
        
        content = await self.page.content()
        if "Your request could not be processed" in content or "Access to this page has been denied" in content:
            await self._save_debug_screenshot(f"profile_block_{profile_url.split('/')[-1]}")
            raise RuntimeError(f"Blocked on profile: {profile_url}")
        
        html = content
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract agent name
        agent_name = None
        name_el = soup.find(['h1', 'h2'])
        if name_el:
            agent_name = name_el.get_text(strip=True)
            agent_name = re.sub(r'[\xae®™].*$', '', agent_name).strip()
            agent_name = re.sub(r'REALTOR.*', '', agent_name, flags=re.I).strip()
        
        # Extract brokerage/office
        brokerage = None
        office_el = soup.find(string=re.compile(r'Brokerage:', re.I))
        if office_el:
            parent = office_el.parent
            if parent:
                text = parent.get_text(strip=True)
                m = re.search(r'Brokerage:\s*(.+)', text, re.I)
                if m:
                    brokerage = m.group(1).strip()
        if not brokerage:
            broker_el = soup.find(class_=re.compile(r'broker|office|company', re.I))
            if broker_el:
                brokerage = broker_el.get_text(strip=True)
        
        # Extract phone
        agent_phone = None
        tel_link = soup.find('a', href=re.compile(r'^tel:', re.I))
        if tel_link:
            agent_phone = tel_link.get_text(strip=True)
        if not agent_phone:
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', soup.get_text())
            if phone_match:
                agent_phone = phone_match.group()
        
        # Extract email
        agent_email = None
        mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
        if mailto:
            m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
            if m:
                agent_email = m.group(0)
        
        if not agent_email:
            # Try to click "Show Email" button via Playwright
            show_email = self.page.locator("button:has-text('Show Email'), a:has-text('Show Email'), button:has-text('Email'), a:has-text('Email')").first
            if await show_email.is_visible(timeout=3000):
                try:
                    await show_email.click()
                    await self._random_delay()
                    updated_html = await self.page.content()
                    soup = BeautifulSoup(updated_html, 'html.parser')
                    mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
                    if mailto:
                        m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
                        if m:
                            agent_email = m.group(0)
                except Exception as e:
                    logger.warning(f"Failed to click show email: {e}")
        
        if not agent_email:
            logger.info(f"No email for {profile_url}; skipping")
            return None
        
        email_norm = agent_email.lower().strip()
        
        return {
            "listing_url": profile_url,
            "platform": "realtor_com",
            "agent_name": agent_name,
            "agent_email": email_norm,
            "agent_phone": agent_phone,
            "office_name": brokerage,
            "city": city,
            "state": state,
            "zip_code": None,
        }
