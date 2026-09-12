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
        Matches public GSM Arena review/opinion URLs such as:
          https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php
          https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php
          https://www.gsmarena.com/reviewcomm-2787.php
        Also accepts gsmarena:// fixture URLs for offline deterministic testing.
        Rejects non-GSM Arena domains, unsupported schemes, and non-review pages.
        """
        if not url:
            return False
        clean = url.strip()

        # Offline test fixtures
        if clean.lower().startswith("gsmarena://"):
            return True

        from urllib.parse import urlparse
        try:
            parsed = urlparse(clean)
        except Exception:
            return False

        if parsed.scheme.lower() not in ("http", "https"):
            return False

        hostname = (parsed.hostname or "").lower()
        if not (hostname == "gsmarena.com" or hostname.endswith(".gsmarena.com")):
            return False

        path = parsed.path.lower()
        # Must be a review, user opinions, or review comments page
        is_review_path = (
            "-reviews-" in path or
            "-review-" in path or
            "reviewcomm-" in path
        )
        if not is_review_path or ".php" not in path:
            return False

        # Reject explicitly non-review sections even if containing keywords
        disallowed_keywords = ("/news", "/glossary", "/contact", "/search", "/picus")
        if any(path.startswith(kw) for kw in disallowed_keywords):
            return False

        return True

    def build_page_url(self, base_url: str, page_num: int) -> str:
        """
        Builds the canonical GSM Arena URL for a specific page:
        Opinions:
          Page 1: https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php
          Page 2: https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557p2.php
        Reviews:
          Page 1: https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php
          Page 2: https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787p2.php
        Comments:
          Page 1: https://www.gsmarena.com/reviewcomm-2787.php
          Page 2: https://www.gsmarena.com/reviewcomm-2787p2.php
        """
        if base_url.startswith("gsmarena://"):
            return f"{base_url}?page={page_num}"

        if page_num <= 1:
            # Normalize to base URL without page suffix if present
            url = re.sub(r"-reviews-(\d+)p\d+\.php", r"-reviews-\1.php", base_url)
            url = re.sub(r"-review-(\d+)p\d+\.php", r"-review-\1.php", url)
            url = re.sub(r"reviewcomm-(\d+)p\d+\.php", r"reviewcomm-\1.php", url)
            return url

        if "-reviews-" in base_url:
            return re.sub(r"-reviews-(\d+)(?:p\d+)?\.php", rf"-reviews-\g<1>p{page_num}.php", base_url)
        elif "-review-" in base_url:
            return re.sub(r"-review-(\d+)(?:p\d+)?\.php", rf"-review-\g<1>p{page_num}.php", base_url)
        elif "reviewcomm-" in base_url:
            return re.sub(r"reviewcomm-(\d+)(?:p\d+)?\.php", rf"reviewcomm-\g<1>p{page_num}.php", base_url)

        return base_url

    def fetch_page_content(self, url: str, page_num: int) -> str:
        """
        Fetches page content from GSM Arena with respectful delay,
        or loads local test fixture if gsmarena:// scheme is requested.
        """
        # Handle local test fixtures for deterministic offline testing
        if url.startswith("gsmarena://"):
            clean_url = url.lower()
            if "malformed" in clean_url:
                fixture_name = "gsmarena_malformed.html"
            elif "fixture-a" in clean_url or "fixture_a" in clean_url:
                fixture_name = "gsmarena_fixture_a.html"
            elif "fixture-b" in clean_url or "fixture_b" in clean_url:
                fixture_name = "gsmarena_fixture_b.html"
            else:
                fixture_name = "gsmarena_sample.html"

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

    def has_next_page(self, html_content: str, current_page: int) -> bool:
        """
        Determines whether there is a subsequent page on GSM Arena:
        1. Checks pagination widget <div class="page"><span class="count">of N</span></div>:
           If total pages N is found, returns current_page < N.
        2. Checks for forward navigation buttons:
           - User opinions: <a class="prevnextbutton" href="..."><i class="...icon-gallery-arrow-right"></i></a>
             (checks that it is not marked with class="disabled" or href="#")
           - Editorial reviews: <a class="next-page" href="...">Next Page</a>
        3. Checks for direct links targeting p{current_page + 1}.php or page={current_page + 1}.
        4. Fallbacks: "Next page" title, or anchor text in (>>, Next, Next >, »).
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Total page count in pagination widget: <div class="page"><span class="count">of 217</span></div>
        page_div = soup.find("div", class_="page")
        if page_div:
            count_elem = page_div.find(class_="count") or page_div
            text = count_elem.get_text(strip=True)
            m = re.search(r"of\s*(\d+)", text, re.I)
            if m:
                total_pages = int(m.group(1))
                return current_page < total_pages

        # 2. Check for forward arrow anchor: e.g. <a class="prevnextbutton" href="...p2.php"><i class="...icon-gallery-arrow-right"></i></a>
        for a in soup.find_all("a"):
            classes = a.get("class") or []
            if "disabled" in classes:
                continue
            href = a.get("href", "")
            if not href or href == "#":
                continue

            # Right arrow icon inside anchor
            if a.find(class_=lambda c: c and ("arrow-right" in str(c) or "icon-next" in str(c))):
                return True

            # Editorial next page button
            if "next-page" in classes or "pages-next" in classes:
                return True

        # 3. Explicit link to current_page + 1: e.g. p2.php or page=2
        expected_p = f"p{current_page + 1}.php"
        expected_page = f"page={current_page + 1}"
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if expected_p in href or expected_page in href:
                return True

        # 4. Standard Next text or title attributes
        for a in soup.find_all("a", href=True):
            classes = a.get("class") or []
            if "disabled" in classes:
                continue
            href = a["href"]
            if href == "#":
                continue
            txt = a.get_text(strip=True).lower()
            title = a.get("title", "").lower()
            if txt in (">>", "next", "next >", "»") or "next page" in title:
                return True

        return False

    def parse_page(self, html_content: str, metadata: Dict[str, Any]) -> List[RawReviewIn]:
        """
        Parses GSM Arena HTML user opinions with BeautifulSoup:
        - Extracts external_review_id from div.user-thread[id]
        - Extracts reviewer nickname from li.uname / li.uname2
        - Extracts review date from li.upost
        - Extracts review text from p.uopin (stripping blockquote replies)
        - Derives product name and brand dynamically if not supplied
        - Sets product_url to target_url for canonical tracking
        - Computes review permalink URL (target URL + #id)
        - Uses safe text normalization (Unicode NFKC, non-NLP)
        """
        soup = BeautifulSoup(html_content, "html.parser")
        reviews_list: List[RawReviewIn] = []
        target_url = metadata.get("target_url", "")

        # Infer product name and brand if not explicitly provided in metadata
        product_name = metadata.get("product_name")
        brand = metadata.get("brand")

        if not product_name:
            h1 = soup.find("h1")
            if h1:
                h1_text = h1.get_text(strip=True)
                # Strip common suffixes like " review", " opinions", " user opinions"
                cleaned_h1 = re.sub(r"\s+(?:review|opinions|user opinions|reviews)$", "", h1_text, flags=re.IGNORECASE).strip()
                product_name = cleaned_h1 or h1_text
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

            # Build permalink URL if target URL is available
            review_url = f"{target_url}#{ext_id}" if target_url and ext_id else None

            reviews_list.append(RawReviewIn(
                product_name=product_name,
                brand=brand,
                product_url=target_url if target_url else None,
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
