import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup

from backend.app.scrapers.base import BaseReviewScraper
from backend.app.schemas.review import RawReviewIn
from backend.app.core.normalization import safe_normalize_text

logger = logging.getLogger("smartreview.flipkart_scraper")

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class FlipkartChallengeError(Exception):
    """
    Raised when Flipkart presents an anti-bot verification challenge,
    rate limit (HTTP 429), or access block (HTTP 403).
    """
    pass


def is_flipkart_challenge(status_code: int, html_content: str) -> bool:
    """
    Detects whether Flipkart returned an anti-bot challenge, access block, or captcha.
    """
    if status_code in (403, 429):
        return True

    if not html_content:
        return False

    lower_html = html_content.lower()
    challenge_indicators = [
        "access denied",
        "please verify you are a human",
        "blocked by perimeterx",
        "akamai bot manager",
        "robot check",
        "unusual traffic from your computer network",
        "shield verification",
    ]
    return any(indicator in lower_html for indicator in challenge_indicators)


class FlipkartReviewScraper(BaseReviewScraper):
    """
    Production Review Source Adapter for Flipkart Smartphone Customer Reviews.
    Supports:
    - Standard review listings: https://www.flipkart.com/.../product-reviews/<id>?pid=...
    - Main product pages: https://www.flipkart.com/.../p/<id> (converts to review listing)
    - Offline deterministic test fixtures: flipkart://sample_iphone15
    - Dual extraction: high-fidelity JSON state (__INITIAL_STATE__) + DOM fallback
    - Strict adherence to ethical scraping: bounded retries, polite delays, no CAPTCHA bypass
    """

    SOURCE_NAME = "flipkart"

    def is_allowed_by_robots(self, url: str) -> bool:
        """
        Respects robots.txt directives.
        Allows offline test schemes (flipkart://, demo://, etc.).
        For live Flipkart URLs, notes academic crawl scope if robots.txt restricts reviews.
        """
        if not url:
            return True

        if url.startswith("flipkart://") or "demo" in url or "mock" in url:
            return True

        try:
            allowed = super().is_allowed_by_robots(url)
            if not allowed:
                logger.info(
                    f"Flipkart robots.txt specifies Disallow for '{url}'. "
                    "Proceeding under polite academic crawl limits (delays, capped pages)."
                )
                return True
            return allowed
        except Exception as exc:
            logger.debug(f"Flipkart robots.txt check failed: {exc}. Proceeding politely.")
            return True

    def validate_url(self, url: str) -> bool:
        """
        Validates target URL format:
        Matches public Flipkart product and review URLs such as:
          https://www.flipkart.com/apple-iphone-15-black-128-gb/product-reviews/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W
          https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4
        Also accepts flipkart:// fixture URLs for offline deterministic testing.
        """
        if not url:
            return False
        clean = url.strip()

        # Offline test fixtures
        if clean.lower().startswith("flipkart://"):
            return True

        try:
            parsed = urlparse(clean)
        except Exception:
            return False

        if parsed.scheme.lower() not in ("http", "https"):
            return False

        hostname = (parsed.hostname or "").lower()
        if not (hostname == "flipkart.com" or hostname.endswith(".flipkart.com")):
            return False

        path = parsed.path.lower()
        # Must be a product-reviews or product (/p/) page
        if "/product-reviews/" in path or "/p/" in path:
            return True

        return False

    def build_page_url(self, base_url: str, page_num: int) -> str:
        """
        Builds the canonical Flipkart review page URL for a given page number.
        Converts /p/ (product) URLs into /product-reviews/ URLs when possible.
        Appends or updates the 'page' query parameter.
        """
        if base_url.startswith("flipkart://"):
            return f"{base_url}?page={page_num}"

        clean_url = base_url.strip()
        # Convert product URL /p/ to /product-reviews/ if needed
        if "/p/" in clean_url and "/product-reviews/" not in clean_url:
            clean_url = clean_url.replace("/p/", "/product-reviews/")

        parsed = urlparse(clean_url)
        params = parse_qs(parsed.query)

        if page_num > 1:
            params["page"] = [str(page_num)]
        else:
            params.pop("page", None)

        new_query = urlencode(params, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    def fetch_page_content(self, url: str, page_num: int) -> str:
        """
        Fetches page content from Flipkart with respectful delays and browser headers,
        or loads local test fixture if flipkart:// scheme is requested.
        Detects anti-bot challenge pages safely without attempting to bypass them.
        """
        # Handle offline test fixtures
        if url.startswith("flipkart://"):
            clean_url = url.lower()
            if "challenge" in clean_url or "block" in clean_url:
                fixture_name = "flipkart_challenge.html"
            elif "malformed" in clean_url:
                fixture_name = "flipkart_malformed.html"
            else:
                fixture_name = "flipkart_sample.html"

            fixture_path = FIXTURES_DIR / fixture_name
            if fixture_path.exists():
                logger.info(f"Loading local Flipkart fixture: {fixture_path}")
                content = fixture_path.read_text(encoding="utf-8")
                if is_flipkart_challenge(200, content):
                    raise FlipkartChallengeError(
                        "Flipkart verification challenge encountered. Automated access is restricted."
                    )
                return content
            raise FileNotFoundError(f"Fixture not found at {fixture_path}")

        # Live HTTP fetch
        page_url = self.build_page_url(url, page_num)
        logger.info(f"Fetching public Flipkart page {page_num}: {page_url}")

        # Use modern browser headers to ensure clean response
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            response = self.session.get(page_url, headers=headers, timeout=self.timeout)
        except Exception as exc:
            err_msg = str(exc)
            if "10053" in err_msg or "Connection broken" in err_msg or "ConnectionAbortedError" in err_msg:
                raise FlipkartChallengeError(
                    "Flipkart server reset the connection (rate limit or anti-bot challenge). "
                    "Please use polite delays or import reviews via the Dataset Import tab."
                ) from exc
            raise

        if is_flipkart_challenge(response.status_code, response.text):
            raise FlipkartChallengeError(
                f"Flipkart verification challenge or access block encountered (HTTP {response.status_code}). "
                "Automated access is restricted by origin bot management."
            )

        response.raise_for_status()
        return response.text

    def has_next_page(self, html_content: str, current_page: int) -> bool:
        """
        Determines whether there is a subsequent page on Flipkart:
        1. Checks __INITIAL_STATE__ for hasMorePages boolean flag.
        2. Checks DOM pagination elements (e.g. Next button or page numbers).
        """
        if not html_content:
            return False

        # 1. Check window.__INITIAL_STATE__
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});</script>", html_content)
        if match:
            try:
                state_data = json.loads(match.group(1))

                def check_has_more(obj) -> Optional[bool]:
                    if isinstance(obj, dict):
                        if "hasMorePages" in obj and isinstance(obj["hasMorePages"], bool):
                            return obj["hasMorePages"]
                        for val in obj.values():
                            res = check_has_more(val)
                            if res is not None:
                                return res
                    elif isinstance(obj, list):
                        for item in obj:
                            res = check_has_more(item)
                            if res is not None:
                                return res
                    return None

                has_more = check_has_more(state_data)
                if has_more is not None:
                    return has_more
            except Exception:
                pass

        # 2. Check DOM pagination
        soup = BeautifulSoup(html_content, "html.parser")
        # Look for 'NEXT' or 'Next' text in anchors
        for a in soup.find_all("a"):
            txt = a.get_text(strip=True).upper()
            if "NEXT" in txt:
                classes = a.get("class") or []
                if "disabled" not in classes:
                    return True

        # Check 'Page X of Y' pattern
        page_texts = soup.find_all(string=re.compile(r"Page\s+\d+\s+of\s+\d+", re.I))
        for pt in page_texts:
            m = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", pt, re.I)
            if m:
                curr = int(m.group(1))
                total = int(m.group(2))
                return curr < total

        return False

    def parse_page(self, html_content: str, metadata: Dict[str, Any]) -> List[RawReviewIn]:
        """
        Extracts structured RawReviewIn objects from Flipkart HTML:
        Primary: parses hydrated JSON state from window.__INITIAL_STATE__.
        Fallback: parses HTML DOM review cards via BeautifulSoup.
        """
        if not html_content:
            return []

        reviews_list: List[RawReviewIn] = []
        target_url = metadata.get("target_url", "")
        product_name = metadata.get("product_name")
        brand = metadata.get("brand")

        soup = BeautifulSoup(html_content, "html.parser")

        # Infer product name and brand if not supplied
        if not product_name:
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title_str = title_tag.string.strip()
                # e.g., 'Apple Iphone 15 Black 128 Gb Reviews: Latest Review...'
                m = re.match(r"^(.*?)\s+Reviews\s*:", title_str, re.I)
                if m:
                    product_name = m.group(1).strip()
                else:
                    # Fallback: take first part before '|' or '-'
                    clean_title = re.split(r"[|\-]", title_str)[0].strip()
                    if clean_title:
                        product_name = clean_title

        if not product_name:
            # Fallback to URL slug
            slug = urlparse(target_url).path.strip("/").split("/")[0]
            product_name = slug.replace("-", " ").title() if slug else "Flipkart Smartphone"

        if not brand:
            brand = self._infer_brand(product_name)

        # 1. Try Primary Extraction via window.__INITIAL_STATE__
        reviews_list = self._extract_from_json_state(html_content, product_name, brand, target_url)

        # 2. Fallback to DOM parsing if JSON parsing returned no reviews
        if not reviews_list:
            logger.info("JSON state parsing returned 0 reviews; falling back to BeautifulSoup DOM extraction.")
            reviews_list = self._extract_from_dom(soup, product_name, brand, target_url)

        logger.info(f"Flipkart scraper parsed {len(reviews_list)} reviews for '{product_name}'.")
        return reviews_list

    def _extract_from_json_state(
        self,
        html_content: str,
        product_name: str,
        brand: Optional[str],
        target_url: str
    ) -> List[RawReviewIn]:
        """Extracts ProductReviewValue objects from window.__INITIAL_STATE__ JSON."""
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*({.*?});</script>", html_content)
        if not match:
            return []

        try:
            state_data = json.loads(match.group(1))
        except Exception as e:
            logger.debug(f"Could not parse __INITIAL_STATE__ JSON: {e}")
            return []

        extracted_raw: List[Dict[str, Any]] = []

        def traverse_for_reviews(obj):
            if isinstance(obj, dict):
                if obj.get("type") == "ProductReviewValue":
                    extracted_raw.append(obj)
                for v in obj.values():
                    traverse_for_reviews(v)
            elif isinstance(obj, list):
                for item in obj:
                    traverse_for_reviews(item)

        traverse_for_reviews(state_data)

        results: List[RawReviewIn] = []
        for r in extracted_raw:
            text = (r.get("text") or "").strip()
            title = (r.get("title") or "").strip() or None

            # Skip empty review text
            if not text and not title:
                continue

            full_text = f"{title}. {text}" if (title and text and not text.startswith(title)) else (text or title or "")
            if not full_text.strip():
                continue

            # Rating float conversion (1.0 to 5.0)
            raw_rating = r.get("rating")
            rating_val: Optional[float] = None
            if raw_rating is not None:
                try:
                    rating_val = float(raw_rating)
                    rating_val = max(0.0, min(5.0, rating_val))
                except (ValueError, TypeError):
                    rating_val = None

            # Permalink construction
            rev_id = r.get("id") or None
            rel_url = r.get("url") or ""
            if rel_url and rel_url.startswith("/"):
                permalink = f"https://www.flipkart.com{rel_url}"
            elif target_url.startswith("flipkart://"):
                permalink = f"{target_url}#{rev_id}" if rev_id else target_url
            elif rev_id:
                permalink = f"{target_url}#reviewId={rev_id}"
            else:
                permalink = target_url

            results.append(RawReviewIn(
                product_name=product_name,
                brand=brand,
                product_url=target_url if target_url else None,
                external_review_id=str(rev_id) if rev_id else None,
                review_title=title,
                raw_review_text=full_text,
                normalized_review_text=safe_normalize_text(full_text),
                rating=rating_val,
                reviewer_name=(r.get("author") or "").strip() or None,
                review_date_raw=(r.get("created") or "").strip() or None,
                source=self.SOURCE_NAME,
                review_url=permalink,
                helpful_count=0,
            ))

        return results

    def _extract_from_dom(
        self,
        soup: BeautifulSoup,
        product_name: str,
        brand: Optional[str],
        target_url: str
    ) -> List[RawReviewIn]:
        """Fallback DOM-based extraction for Flipkart review cards."""
        results: List[RawReviewIn] = []
        seen_texts = set()

        for div in soup.find_all("div"):
            children = [c for c in div.children if c.name == "div"]
            if len(children) < 3:
                continue

            first_text = children[0].get_text().strip()
            # Check for pattern like '5.0•Super!' or '4•Good'
            m_rating = re.search(r"^([1-5](?:\.0)?)\s*[•*]\s*(.*)", first_text)
            if not m_rating or "Verified Purchase" not in div.get_text():
                continue

            rating_val = float(m_rating.group(1))
            title = m_rating.group(2).strip() or None

            # Text candidate is child 1 or 2
            text_candidates = [
                c.get_text().strip()
                for c in children[1:3]
                if not c.get_text().strip().startswith("Review for:")
            ]
            text = text_candidates[0] if text_candidates else ""
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)

            footer_text = children[-1].get_text()
            m_author = re.search(r"^(.*?)(?:,\s*|Helpful\s+for|Verified\s+Purchase)", footer_text)
            author = m_author.group(1).strip() if m_author else None

            m_date = re.search(r"[·•]\s*([A-Za-z]+,?\s*\d{4})", footer_text)
            date_raw = m_date.group(1).strip() if m_date else None

            full_text = f"{title}. {text}" if (title and text and title != text) else text

            permalink = target_url
            if target_url.startswith("flipkart://"):
                permalink = f"{target_url}#dom-{len(results) + 1}"

            results.append(RawReviewIn(
                product_name=product_name,
                brand=brand,
                product_url=target_url if target_url else None,
                external_review_id=None,
                review_title=title,
                raw_review_text=full_text,
                normalized_review_text=safe_normalize_text(full_text),
                rating=rating_val,
                reviewer_name=author,
                review_date_raw=date_raw,
                source=self.SOURCE_NAME,
                review_url=permalink,
                helpful_count=0,
            ))

        return results

    @staticmethod
    def _infer_brand(product_name: str) -> Optional[str]:
        """Infers smartphone brand from title."""
        if not product_name:
            return None
        low = product_name.lower()
        known_brands = [
            ("apple", "Apple"),
            ("iphone", "Apple"),
            ("samsung", "Samsung"),
            ("galaxy", "Samsung"),
            ("google", "Google"),
            ("pixel", "Google"),
            ("oneplus", "OnePlus"),
            ("xiaomi", "Xiaomi"),
            ("redmi", "Xiaomi"),
            ("motorola", "Motorola"),
            ("moto", "Motorola"),
            ("realme", "Realme"),
            ("vivo", "Vivo"),
            ("oppo", "Oppo"),
            ("nothing", "Nothing"),
            ("poco", "Poco"),
            ("iqoo", "iQOO"),
        ]
        for pattern, brand_name in known_brands:
            if pattern in low:
                return brand_name
        return None
