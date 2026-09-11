import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from backend.app.scrapers.base import BaseReviewScraper
from backend.app.schemas.review import RawReviewIn
from backend.app.core.normalization import safe_normalize_text

logger = logging.getLogger("smartreview.gsmarena_scraper")

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

class GSMArenaReviewScraper(BaseReviewScraper):
    """
    Production Review Source Adapter for GSM Arena User Opinions & Reviews.
    Publicly accessible smartphone user reviews with:
    - Zero login / credentials required
    - Zero CAPTCHA / anti-bot bypass
    - robots.txt compliant
    - Bounded retries, polite delays, and identifiable User-Agent
    """

    SOURCE_NAME = "gsmarena"

    def validate_url(self, url: str) -> bool:
        """
        Validates target URL format:
        Matches public GSM Arena review URLs such as:
          https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php
        Also accepts gsmarena:// fixture URLs for offline deterministic testing.
        """
        if not url:
            return False
        clean = url.strip().lower()

        # Offline test fixtures
        if clean.startswith("gsmarena://"):
            return True

        # Public GSM Arena review page pattern
        if "gsmarena.com/" in clean and "-reviews-" in clean:
            return True

        return False

    def build_page_url(self, base_url: str, page_num: int) -> str:
        """
        Builds the canonical GSM Arena URL for a specific page:
        Page 1: https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php
        Page 2: https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557p2.php
        Page N: https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557pN.php
        """
        if base_url.startswith("gsmarena://"):
            return f"{base_url}?page={page_num}"

        if page_num <= 1:
            # Normalize to base URL without page suffix if present
            return re.sub(r"-reviews-(\d+)p\d+\.php", r"-reviews-\1.php", base_url)

        return re.sub(r"-reviews-(\d+)(?:p\d+)?\.php", rf"-reviews-\g<1>p{page_num}.php", base_url)

    def fetch_page_content(self, url: str, page_num: int) -> str:
        """
        Fetches page content from GSM Arena with respectful delay,
        or loads local test fixture if gsmarena:// scheme is requested.
        """
        # Handle local test fixtures for deterministic offline testing
        if url.startswith("gsmarena://"):
            fixture_name = "gsmarena_malformed.html" if "malformed" in url else "gsmarena_sample.html"
            fixture_path = FIXTURES_DIR / fixture_name
            if fixture_path.exists():
                logger.info(f"Loading local GSM Arena fixture: {fixture_path}")
                return fixture_path.read_text(encoding="utf-8")
            raise FileNotFoundError(f"Fixture not found at {fixture_path}")

        # Live HTTP fetch for public source
        page_url = self.build_page_url(url, page_num)
        logger.info(f"Fetching public GSM Arena page {page_num}: {page_url}")

        response = self.session.get(page_url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def parse_page(self, html_content: str, metadata: Dict[str, Any]) -> List[RawReviewIn]:
        """
        Parses GSM Arena HTML user opinions with BeautifulSoup:
        - Extracts external_review_id from div.user-thread[id]
        - Extracts reviewer nickname from li.uname / li.uname2
        - Extracts review date from li.upost
        - Extracts review text from p.uopin (stripping blockquote replies)
        - Computes review permalink URL (canonical URL + #id)
        - Uses safe text normalization (Unicode NFKC, non-NLP)
        """
        soup = BeautifulSoup(html_content, "html.parser")
        reviews_list: List[RawReviewIn] = []

        # Infer product name and brand if not passed in metadata
        product_name = metadata.get("product_name")
        brand = metadata.get("brand")

        if not product_name:
            h1 = soup.find("h1")
            if h1:
                product_name = h1.get_text(strip=True)
            elif soup.title:
                title_text = soup.title.get_text(strip=True)
                product_name = title_text.split("-")[0].strip() if "-" in title_text else title_text

        if not product_name:
            product_name = "Smartphone"

        if not brand:
            brand = product_name.split()[0] if product_name else "Unknown"

        # Locate review containers
        opinion_threads = soup.find_all("div", class_="user-thread")
        for thread in opinion_threads:
            ext_id = thread.get("id")

            # Extract reviewer name
            author = "Anonymous"
            uname_el = thread.find("li", class_=["uname", "uname2"])
            if uname_el and uname_el.get_text(strip=True):
                author = uname_el.get_text(strip=True)

            # Extract review date
            date_raw = None
            upost_el = thread.find("li", class_="upost")
            if upost_el:
                date_raw = upost_el.get_text(strip=True)

            # Extract review text from p.uopin
            body_el = thread.find("p", class_="uopin")
            if not body_el:
                continue

            # Strip quotation replies (<span class="uinreply">, etc.) to get authentic user opinion
            for reply_span in body_el.find_all("span", class_=["uinreply", "uinreply-msg"]):
                reply_span.decompose()

            raw_text = body_el.get_text(strip=True)
            if not raw_text or len(raw_text) < 3:
                # Ignore empty or deleted comment placeholders
                continue

            # Safe normalization (Unicode NFKC, space collapsing, no NLP)
            normalized_text = safe_normalize_text(raw_text)

            # Build permalink URL if target URL / canonical URL is available
            target_url = metadata.get("target_url", "")
            review_url = f"{target_url}#{ext_id}" if target_url and ext_id else None

            reviews_list.append(RawReviewIn(
                product_name=product_name,
                brand=brand,
                external_review_id=str(ext_id) if ext_id else None,
                review_title=None,
                raw_review_text=raw_text,
                normalized_review_text=normalized_text,
                rating=None,  # GSM Arena opinions are qualitative comments
                reviewer_name=author,
                review_date_raw=date_raw,
                source=self.SOURCE_NAME,
                review_url=review_url,
                helpful_count=0
            ))

        return reviews_list
