"""Keller Williams agent directory scraper using async Playwright."""
import os
import logging
import re
import asyncio
import random
from typing import List, Dict, Optional, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class KWAgentsScraper:
    def __init__(self, headless: bool = True, proxy: Optional[str] = None, debug_dir: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.debug_dir = debug_dir
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        # Default delays; can be configured later
        self.delay_min = 2
        self.delay_max = 5

    async def _init_browser(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ]
        if self.proxy:
            browser_args.append(f'--proxy-server={self.proxy}')
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {'width': 1920, 'height': 1080},
            "locale": 'en-US',
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
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def _random_delay(self):
        await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))

    async def _save_debug_screenshot(self, name: str):
        if self.debug_dir and self.page:
            import os
            os.makedirs(self.debug_dir, exist_ok=True)
            path = os.path.join(self.debug_dir, f"{name}.png")
            await self.page.screenshot(path=path, full_page=True)
            logger.info(f"Saved screenshot: {path}")

    def _parse_slug(self, slug: str) -> tuple[str, str]:
        """Convert slug like 'los-angeles-ca' to ('Los Angeles', 'CA')."""
        slug_clean = slug.rstrip('/').split('/')[-1]
        parts = slug_clean.split('-')
        if len(parts) < 2:
            raise ValueError(f"Invalid slug format: {slug}")
        state = parts[-1].upper()
        city = ' '.join(part.capitalize() for part in parts[:-1])
        return city, state

    async def _check_cloudflare(self) -> bool:
        """Check if current page is a Cloudflare challenge page."""
        try:
            title = await self.page.title()
            if title and ('just a moment' in title.lower() or 'cloudflare' in title.lower()):
                return True
        except:
            pass
        try:
            content = await self.page.content()
            if 'performing security verification' in content.lower() or 'cloudflare' in content.lower():
                return True
        except:
            pass
        return False

    async def _wait_for_cloudflare(self, timeout=30):
        """Wait for Cloudflare challenge to complete."""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if not await self._check_cloudflare():
                return True
            await asyncio.sleep(1)
        return False

    async def _get_agent_links(self) -> List[str]:
        """Extract agent profile links from the directory page."""
        try:
            await self.page.wait_for_selector("a[href*='/agent/'], a[href*='/profile/']", timeout=10000)
        except:
            pass
        links = []
        # Use JavaScript to get all matching anchor hrefs
        anchors = await self.page.locator("a[href*='/agent/'], a[href*='/profile/']").all()
        for a in anchors:
            try:
                href = await a.get_attribute("href")
                if href:
                    if href.startswith('http'):
                        full_url = href.split('?')[0]
                    elif href.startswith('/'):
                        full_url = f"https://www.kw.com{href.split('?')[0]}"
                    else:
                        continue
                    if full_url not in links:
                        links.append(full_url)
            except:
                continue
        # Deduplicate while preserving order
        return list(dict.fromkeys(links))

    async def _scroll_to_bottom(self, max_scrolls=10, pause=2):
        """Scroll down to trigger lazy loading."""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        for _ in range(max_scrolls):
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(pause)
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    async def _extract_agent_data(self, url: str, city: str, state: str) -> Optional[Dict]:
        """Extract agent info from profile page."""
        try:
            await self.page.goto(url, timeout=30000)
            await self._random_delay()
            # Check Cloudflare challenge
            if await self._check_cloudflare():
                logger.info(f"Cloudflare challenge on {url}, waiting...")
                await self._save_debug_screenshot(f"kw_cf_profile_{url.split('/')[-1]}")
                if not await self._wait_for_cloudflare(timeout=20):
                    logger.error(f"Cloudflare challenge did not resolve on {url}")
                    return None
            try:
                await self.page.wait_for_selector("body", timeout=5000)
            except:
                pass
            await self._save_debug_screenshot(f"kw_profile_{url.split('/')[-1]}")
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract agent name
            name = None
            name_el = soup.find(['h1', 'h2', 'h3'], class_=re.compile(r'agent-name|profile-name|title-name|agent-title', re.I))
            if not name_el:
                for heading in soup.find_all(['h1', 'h2']):
                    text = heading.get_text(strip=True)
                    if text and len(text) < 100:
                        name = text
                        break
            else:
                name = name_el.get_text(strip=True)
            
            # Extract email
            email = None
            mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
            if mailto:
                match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", mailto['href'])
                if match:
                    email = match.group(0)
            if not email:
                text = soup.get_text()
                match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
                if match:
                    email = match.group(0)
            
            # Extract phone
            phone = None
            tel_link = soup.find('a', href=re.compile(r'^tel:', re.I))
            if tel_link:
                phone = tel_link.get_text(strip=True) or tel_link['href'].replace('tel:', '').strip()
            if not phone:
                phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", soup.get_text())
                if phone_match:
                    phone = phone_match.group()
            
            # Extract team/office name
            team = None
            team_el = soup.find(['span', 'div', 'p', 'li'], class_=re.compile(r'team|office|branch|location|office-name', re.I))
            if team_el:
                team = team_el.get_text(strip=True)
            if not team:
                text = soup.get_text()
                m = re.search(r"(?:Office|Team|Branch|Location)[:\s]*([^\n\r]+)", text, re.I)
                if m:
                    team = m.group(1).strip()
                    team = re.sub(r'\s+', ' ', team)
            
            if not email:
                logger.warning(f"Skipping agent at {url}: no email found")
                return None
            
            return {
                'agent_name': name,
                'agent_email': email,
                'agent_phone': phone,
                'team_name': team,
                'city': city,
                'state': state,
                'profile_url': url
            }
        except Exception as e:
            logger.error(f"Error extracting agent data from {url}: {e}")
            return None

    async def scrape_city(self, slug: str, limit: int = 20) -> List[Dict]:
        """
        Scrape agents for a given city-state slug (e.g., 'los-angeles-ca').
        Returns list of agent data dicts.
        """
        city, state = self._parse_slug(slug)
        logger.info(f"Scraping KW agents for {city}, {state} (slug: {slug})")
        url = f"https://www.kw.com/agents/{slug}"
        await self._init_browser()
        try:
            await self.page.goto(url, timeout=60000)
            await self._random_delay()
            await self._save_debug_screenshot(f"kw_dir_{city.lower()}_{state.lower()}")
            # Check for Cloudflare challenge
            if await self._check_cloudflare():
                logger.info("Cloudflare challenge detected, waiting...")
                await self._save_debug_screenshot(f"kw_cf_{city.lower()}_{state.lower()}")
                if not await self._wait_for_cloudflare(timeout=30):
                    raise RuntimeError("Cloudflare challenge did not resolve")
            # Scroll to load all agents (lazy load)
            await self._scroll_to_bottom(max_scrolls=5, pause=2)
            await self._save_debug_screenshot(f"kw_scrolled_{city.lower()}_{state.lower()}")
            # Save HTML for selector debugging
            if self.debug_dir:
                html_path = os.path.join(self.debug_dir, f"kw_html_{city.lower()}_{state.lower()}.html")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(await self.page.content())
                logger.info(f"Saved HTML: {html_path}")
            # Get agent profile links
            agent_links = await self._get_agent_links()
            logger.info(f"Found {len(agent_links)} agent links on directory page")
            if limit and len(agent_links) > limit:
                agent_links = agent_links[:limit]
            agents_data = []
            for idx, link in enumerate(agent_links):
                logger.debug(f"Processing agent profile: {link}")
                data = await self._extract_agent_data(link, city, state)
                if data:
                    agents_data.append(data)
                await self._random_delay()
            logger.info(f"Extracted {len(agents_data)} agents for {city}, {state}")
            return agents_data
        finally:
            await self._close_browser()

    async def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        BaseLeadSource interface.
        Expected config: {
            'city': 'City Name',
            'state': 'ST',
            'limit': 20 (optional)
        }
        """
        city = config.get("city")
        state = config.get("state")
        if not city or not state:
            raise ValueError("city and state are required")
        slug = f"{city.lower().replace(' ', '-')}-{state.lower()}"
        limit = config.get("limit", 20)
        return await self.scrape_city(slug, limit)
