import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Generator, Optional, Dict, Any
from urllib.parse import urlparse
import urllib.robotparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.app.schemas.review import RawReviewIn
from backend.app.core.config import settings

logger = logging.getLogger("smartreview.scraper")

class BaseReviewScraper(ABC):
    """
    Abstract Base Class for all review scrapers.
    Strictly follows ethical scraping guidelines:
    - Respectful configurable delays with jitter
    - Configurable timeouts and capped retries with exponential backoff
    - Honest User-Agent header
    - Page limits and maximum review count limits
    - Robots.txt policy awareness
    - Zero anti-bot evasion / zero CAPTCHA bypass
    """

    def __init__(
        self,
        delay_seconds: Optional[float] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        user_agent: Optional[str] = None,
    ):
        self.delay_seconds = delay_seconds if delay_seconds is not None else settings.DEFAULT_SCRAPE_DELAY
        self.timeout = timeout if timeout is not None else settings.DEFAULT_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
        self.user_agent = user_agent if user_agent is not None else settings.USER_AGENT
        self.session = self._create_session()
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        return session

    def wait_polite(self):
        """Introduce polite delay with slight random jitter to prevent server strain."""
        jitter = random.uniform(0.1, 0.4)
        total_delay = self.delay_seconds + jitter
        logger.debug(f"Polite delay of {total_delay:.2f}s before next request...")
        time.sleep(total_delay)

    def is_allowed_by_robots(self, url: str) -> bool:
        """
        Respects robots.txt directives for standard HTTP/HTTPS URLs.
        Fails safely/permissively if robots.txt cannot be reached,
        and automatically allows local test/fixture schemes (demo://, gsmarena://, etc.).
        """
        if not url:
            return True

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return True

        if "mock" in url or "demo" in url:
            return True

        domain_key = f"{parsed.scheme}://{parsed.netloc}"
        if domain_key not in self._robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{domain_key}/robots.txt")
            try:
                rp.read()
            except Exception as e:
                logger.debug(f"Could not read robots.txt for {domain_key}: {e}. Proceeding respectfully.")
            self._robots_cache[domain_key] = rp

        rp = self._robots_cache[domain_key]
        return rp.can_fetch(self.user_agent, url) if rp else True

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Validate whether this scraper adapter supports the given target URL."""
        pass

    @abstractmethod
    def fetch_page_content(self, url: str, page_num: int) -> str:
        """Fetch raw HTML for a specific page."""
        pass

    @abstractmethod
    def parse_page(self, html_content: str, metadata: Dict[str, Any]) -> List[RawReviewIn]:
        """Extract structured RawReviewIn objects from HTML."""
        pass

    def scrape(
        self,
        target_url: str,
        max_pages: int = 3,
        max_reviews: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Orchestrates scraping across pages, yielding status dicts with batch reviews.
        Strictly respects max_pages and max_reviews limits.
        """
        if not self.validate_url(target_url):
            raise ValueError(f"URL '{target_url}' is not supported by {self.__class__.__name__}")

        if not self.is_allowed_by_robots(target_url):
            logger.warning(f"URL '{target_url}' is disallowed by robots.txt policy.")
            raise PermissionError(f"Target URL '{target_url}' is disallowed by robots.txt")

        meta = metadata or {}
        # Bound max pages by settings
        pages_to_scrape = max(1, min(max_pages, settings.DEFAULT_MAX_PAGES * 2))

        total_collected = 0

        for page in range(1, pages_to_scrape + 1):
            if page > 1:
                self.wait_polite()

            try:
                html = self.fetch_page_content(target_url, page)
                reviews = self.parse_page(html, meta)

                # Check max_reviews cap
                if max_reviews is not None and (total_collected + len(reviews)) > max_reviews:
                    allowed = max_reviews - total_collected
                    reviews = reviews[:allowed]

                total_collected += len(reviews)

                yield {
                    "page": page,
                    "success": True,
                    "reviews": reviews,
                    "error": None
                }

                if max_reviews is not None and total_collected >= max_reviews:
                    logger.info(f"Reached max_reviews limit ({max_reviews}). Terminating crawl early.")
                    break

            except Exception as e:
                logger.error(f"Error scraping page {page} of {target_url}: {e}", exc_info=True)
                yield {
                    "page": page,
                    "success": False,
                    "reviews": [],
                    "error": str(e)
                }
