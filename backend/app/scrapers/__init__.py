from backend.app.scrapers.base import BaseReviewScraper
from backend.app.scrapers.demo_scraper import DemoReviewScraper
from backend.app.scrapers.gsmarena_scraper import GSMArenaReviewScraper
from backend.app.scrapers.registry import ScraperRegistry

__all__ = [
    "BaseReviewScraper",
    "DemoReviewScraper",
    "GSMArenaReviewScraper",
    "ScraperRegistry",
]
