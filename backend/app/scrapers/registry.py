from typing import Dict, Type
from backend.app.scrapers.base import BaseReviewScraper
from backend.app.scrapers.demo_scraper import DemoReviewScraper
from backend.app.scrapers.gsmarena_scraper import GSMArenaReviewScraper

class ScraperRegistry:
    _registry: Dict[str, Type[BaseReviewScraper]] = {
        "demo": DemoReviewScraper,
        "gsmarena": GSMArenaReviewScraper,
    }

    @classmethod
    def register(cls, name: str, scraper_cls: Type[BaseReviewScraper]):
        cls._registry[name.lower()] = scraper_cls

    @classmethod
    def get(cls, name: str) -> Type[BaseReviewScraper]:
        scraper_cls = cls._registry.get(name.lower())
        if not scraper_cls:
            raise ValueError(f"Unknown scraper type '{name}'. Registered: {list(cls._registry.keys())}")
        return scraper_cls

    @classmethod
    def available_scrapers(cls) -> list:
        return list(cls._registry.keys())
