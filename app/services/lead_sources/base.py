from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLeadSource(ABC):
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
    
    @abstractmethod
    def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape leads according to config and return normalized lead data dicts."""
        pass
