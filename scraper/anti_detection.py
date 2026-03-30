"""
Anti-detection utilities for web scraping
"""
import random
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class StealthWrapper:
    """Provides stealth headers and behaviors for scraping"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    @staticmethod
    def get_random_headers(extra: Optional[dict] = None) -> dict:
        headers = {
            "User-Agent": random.choice(StealthWrapper.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        if extra:
            headers.update(extra)
        return headers
    
    @staticmethod
    def random_delay(min_sec: float, max_sec: float):
        """Sleep for a random duration to avoid rate limiting detection"""
        delay = random.uniform(min_sec, max_sec)
        logger.debug(f"Sleeping for {delay:.2f}s")
        time.sleep(delay)
    
    @staticmethod
    def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 2):
        """Retry a function with exponential backoff"""
        for attempt in range(1, max_retries + 1):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries:
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

def rotate_proxy(proxy_pool: list) -> Optional[str]:
    """Get next proxy from pool (round-robin)"""
    if not proxy_pool:
        return None
    # Simple implementation - in production, use a more robust rotator
    return random.choice(proxy_pool)