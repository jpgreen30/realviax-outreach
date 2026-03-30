"""
Scraper package
"""
from .platforms.zillow import ZillowScraper
from .platforms.redfin import RedfinScraper
from .platforms.realtor_com import RealtorComScraper
from .extractors import ListingExtractor
from .anti_detection import StealthWrapper

__all__ = [
    "ZillowScraper",
    "RedfinScraper",
    "RealtorComScraper",
    "ListingExtractor",
    "StealthWrapper"
]

def get_scraper(platform: str, **kwargs):
    """Factory function to get appropriate scraper"""
    scrapers = {
        "zillow": ZillowScraper,
        "redfin": RedfinScraper,
        "realtor_com": RealtorComScraper,
    }
    scraper_class = scrapers.get(platform)
    if not scraper_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return scraper_class(**kwargs)