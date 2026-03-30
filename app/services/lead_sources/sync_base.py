"""Lead source scrapers base classes"""
import os
import json
import logging
import time
import random
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# Default delays if settings unavailable
DEFAULT_DELAY_MIN = 2
DEFAULT_DELAY_MAX = 5

class BaseLeadSource:
    """Base class for lead source scrapers using Playwright."""
    def __init__(self, headless: bool = True):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.headless = headless
        self.cookies_file = None  # optional
        self.credentials = None
        # Attempt to load settings for scrape delays, fallback to defaults
        try:
            from app.core.config import settings
            self.delay_min = settings.SCRAPE_DELAY_MIN
            self.delay_max = settings.SCRAPE_DELAY_MAX
        except Exception:
            self.delay_min = DEFAULT_DELAY_MIN
            self.delay_max = DEFAULT_DELAY_MAX
        self._init_browser()

    def _init_browser(self):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        # Stealth arguments to avoid detection
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/Los_Angeles',
        )
        # Evaluate js to hide automation
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3] });
        """)
        self.page = self.context.new_page()

    def _close_browser(self):
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
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
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_browser()
