import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from backend.app.scrapers.base import BaseReviewScraper
from backend.app.schemas.review import RawReviewIn

logger = logging.getLogger("smartreview.demo_scraper")

DEMO_SMARTPHONES = [
    {
        "name": "Apple iPhone 15 Pro",
        "brand": "Apple",
        "url_slug": "iphone-15-pro",
        "reviews": [
            # Page 1
            [
                {
                    "title": "Incredible camera and lightweight titanium frame",
                    "text": "The titanium design makes a noticeable difference in hand. The 5x optical zoom on the telephoto lens is sharp even in lower light. Battery easily lasts all day with normal productivity and media consumption.",
                    "rating": 4.8,
                    "author": "TechEnthusiast88",
                    "date": "2024-03-15",
                    "helpful": 42,
                    "ext_id": "demo-iph-001"
                },
                {
                    "title": "USB-C transition is finally here",
                    "text": "Finally having USB-C on an iPhone simplifies my travel charger setup tremendously. Performance with the A17 Pro chip is lightning fast with zero thermal throttling during gaming sessions.",
                    "rating": 4.5,
                    "author": "GadgetFanatic",
                    "date": "2024-03-12",
                    "helpful": 19,
                    "ext_id": "demo-iph-002"
                },
                {
                    "title": "Action button is handy but iOS 17 is familiar",
                    "text": "The customizable Action Button is a great physical shortcut for the flashlight and mute switch. Display brightness outdoors in direct sunlight is class-leading.",
                    "rating": 4.2,
                    "author": "MobileGuru",
                    "date": "2024-03-08",
                    "helpful": 11,
                    "ext_id": "demo-iph-003"
                }
            ],
            # Page 2
            [
                {
                    "title": "Great phone, but premium price tag",
                    "text": "Build quality is unmatched, but it gets moderately warm during rapid fast charging. Storage upgrades remain expensive, though overall performance is flawless.",
                    "rating": 4.0,
                    "author": "PracticalBuyer",
                    "date": "2024-03-01",
                    "helpful": 15,
                    "ext_id": "demo-iph-004"
                },
                {
                    "title": "Incredible camera and lightweight titanium frame", # Intentional duplicate for deduplication testing!
                    "text": "The titanium design makes a noticeable difference in hand. The 5x optical zoom on the telephoto lens is sharp even in lower light. Battery easily lasts all day with normal productivity and media consumption.",
                    "rating": 4.8,
                    "author": "TechEnthusiast88",
                    "date": "2024-03-15",
                    "helpful": 42,
                    "ext_id": "demo-iph-001"
                },
                {
                    "title": "Flawless screen and speaker acoustic fidelity",
                    "text": "Dynamic Island integration with flight tracking and timers is delightfully polished. Spatial audio through the stereo speakers is surprisingly deep and resonant.",
                    "rating": 4.7,
                    "author": "AudiophileTech",
                    "date": "2024-02-26",
                    "helpful": 8,
                    "ext_id": "demo-iph-005"
                }
            ],
            # Page 3
            [
                {
                    "title": "Solid upgrade from an older generation",
                    "text": "Upgraded from an iPhone 11 and the OLED 120Hz ProMotion screen is night and day difference. FaceID is instantaneous and cameras excel in night mode.",
                    "rating": 4.9,
                    "author": "EverydayShopper",
                    "date": "2024-02-18",
                    "helpful": 24,
                    "ext_id": "demo-iph-006"
                }
            ]
        ]
    },
    {
        "name": "Samsung Galaxy S24 Ultra",
        "brand": "Samsung",
        "url_slug": "galaxy-s24-ultra",
        "reviews": [
            # Page 1
            [
                {
                    "title": "Anti-reflective flat display is a masterclass",
                    "text": "The Gorilla Armor glass cuts reflections dramatically outdoors. The flat display makes S-Pen note taking significantly more practical around the edges. Battery life consistently hits 8 hours screen-on time.",
                    "rating": 4.9,
                    "author": "AndroidPowerUser",
                    "date": "2024-03-14",
                    "helpful": 53,
                    "ext_id": "demo-s24-001"
                },
                {
                    "title": "AI features are useful, zoom clarity is top tier",
                    "text": "The 5x optical sensor paired with digital zoom delivers crisp 10x photos. Live call translation worked well on my recent overseas trip. One UI 6.1 feels snappy.",
                    "rating": 4.6,
                    "author": "GlobeTrotter",
                    "date": "2024-03-10",
                    "helpful": 28,
                    "ext_id": "demo-s24-002"
                }
            ],
            # Page 2
            [
                {
                    "title": "Bulky in pocket but outstanding productivity monster",
                    "text": "Phone is large and boxy, making one-handed operation tricky. However, the screen estate and multitasking capabilities via split screen are unrivaled for productivity.",
                    "rating": 4.3,
                    "author": "BusinessExec",
                    "date": "2024-03-02",
                    "helpful": 14,
                    "ext_id": "demo-s24-003"
                },
                {
                    "title": "Superb battery endurance and fast charging",
                    "text": "45W fast charging gets me from 10% to 70% in roughly 30 minutes. The Snapdragon 8 Gen 3 handles high-framerate 3D gaming effortlessly without hot spots.",
                    "rating": 4.8,
                    "author": "GamerX",
                    "date": "2024-02-25",
                    "helpful": 32,
                    "ext_id": "demo-s24-004"
                }
            ]
        ]
    },
    {
        "name": "Google Pixel 8 Pro",
        "brand": "Google",
        "url_slug": "pixel-8-pro",
        "reviews": [
            # Page 1
            [
                {
                    "title": "Pure Android experience with benchmark camera processing",
                    "text": "Camera skin tones with Real Tone are the most authentic on any smartphone. Magic Editor and Audio Magic Eraser actually work effectively for family photos and video logs.",
                    "rating": 4.7,
                    "author": "PhotoJournalist",
                    "date": "2024-03-11",
                    "helpful": 37,
                    "ext_id": "demo-px8-001"
                },
                {
                    "title": "Super Actua display is brilliant",
                    "text": "The screen hits 2400 nits peak brightness and looks vibrant. Clean Android without pre-installed bloatware is refreshing. 7 years of promised OS updates is peace of mind.",
                    "rating": 4.5,
                    "author": "CleanROM",
                    "date": "2024-03-05",
                    "helpful": 21,
                    "ext_id": "demo-px8-002"
                }
            ]
        ]
    }
]

def generate_mock_html(phone_data: Dict[str, Any], page_num: int) -> str:
    """Generates realistic semantic HTML representing an e-commerce review page."""
    reviews_pages = phone_data.get("reviews", [])
    page_index = page_num - 1
    reviews_for_page = reviews_pages[page_index] if 0 <= page_index < len(reviews_pages) else []

    html_parts = [
        f'<!DOCTYPE html>',
        f'<html lang="en">',
        f'<head><title>{phone_data["name"]} Customer Reviews - Page {page_num}</title></head>',
        f'<body>',
        f'<div class="product-header" data-product="{phone_data["name"]}" data-brand="{phone_data["brand"]}">',
        f'  <h1 class="product-title">{phone_data["name"]}</h1>',
        f'  <span class="product-brand">{phone_data["brand"]}</span>',
        f'</div>',
        f'<div class="reviews-container">'
    ]

    for rev in reviews_for_page:
        html_parts.append(f'''
        <article class="review-item" data-review-id="{rev['ext_id']}">
            <h3 class="review-title">{rev['title']}</h3>
            <div class="review-rating" data-score="{rev['rating']}">{rev['rating']} out of 5 stars</div>
            <div class="review-author">{rev['author']}</div>
            <time class="review-date" datetime="{rev['date']}">{rev['date']}</time>
            <p class="review-body">{rev['text']}</p>
            <span class="helpful-votes">{rev['helpful']} people found this helpful</span>
        </article>
        ''')

    html_parts.extend([
        f'</div>',
        f'<div class="pagination" data-current-page="{page_num}" data-total-pages="{len(reviews_pages)}"></div>',
        f'</body></html>'
    ])
    return "\n".join(html_parts)

class DemoReviewScraper(BaseReviewScraper):
    """
    Demo/Test Scraper adapter.
    Parses local semantic HTML using BeautifulSoup.
    Allows thorough, resilient testing and evaluation without relying on flaky third-party websites.
    """

    def validate_url(self, url: str) -> bool:
        """Accepts demo:// URLs or mock URLs pointing to test catalogs."""
        url_lower = url.lower()
        return (
            url_lower.startswith("demo://") or
            "demo-catalog.internal" in url_lower or
            "mock-review" in url_lower or
            url_lower == "demo"
        )

    def _resolve_phone_data(self, url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        # Try matching by product_name in metadata first
        req_name = metadata.get("product_name", "").strip().lower()
        if req_name:
            for phone in DEMO_SMARTPHONES:
                if req_name in phone["name"].lower() or phone["name"].lower() in req_name:
                    return phone

        # Otherwise match from URL slug
        for phone in DEMO_SMARTPHONES:
            if phone["url_slug"] in url.lower() or phone["name"].lower() in url.lower():
                return phone

        # Default fallback to first phone
        return DEMO_SMARTPHONES[0]

    def fetch_page_content(self, url: str, page_num: int) -> str:
        """Generates dynamic semantic HTML for the requested smartphone and page."""
        # For demo, metadata can be inferred from URL or fallback
        phone = self._resolve_phone_data(url, {})
        return generate_mock_html(phone, page_num)

    def parse_page(self, html_content: str, metadata: Dict[str, Any]) -> List[RawReviewIn]:
        """
        Parses HTML using BeautifulSoup with standard CSS selectors.
        Extracts structured reviews into RawReviewIn objects.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        reviews_list: List[RawReviewIn] = []

        product_header = soup.find("div", class_="product-header")
        default_product = metadata.get("product_name") or (product_header.get("data-product") if product_header else "Unknown Smartphone")
        default_brand = metadata.get("brand") or (product_header.get("data-brand") if product_header else "Unknown")

        from backend.app.core.normalization import safe_normalize_text

        review_cards = soup.find_all("article", class_="review-item")
        for card in review_cards:
            ext_id = card.get("data-review-id")
            title_el = card.find("h3", class_="review-title")
            title = title_el.get_text(strip=True) if title_el else None

            body_el = card.find("p", class_="review-body")
            raw_text = body_el.get_text(strip=True) if body_el else ""
            if not raw_text:
                continue

            # Safe normalization (Unicode NFKC, collapsed whitespace, non-NLP)
            normalized_text = safe_normalize_text(raw_text)

            rating_el = card.find("div", class_="review-rating")
            rating = None
            if rating_el:
                score_attr = rating_el.get("data-score")
                if score_attr:
                    try:
                        rating = float(score_attr)
                    except ValueError:
                        pass

            author_el = card.find("div", class_="review-author")
            author = author_el.get_text(strip=True) if author_el else None

            date_el = card.find("time", class_="review-date")
            date_raw = date_el.get_text(strip=True) if date_el else None

            helpful_el = card.find("span", class_="helpful-votes")
            helpful_count = 0
            if helpful_el:
                txt = helpful_el.get_text()
                digits = "".join(ch for ch in txt if ch.isdigit())
                if digits:
                    helpful_count = int(digits)

            # Simulated permalink for Tier 2 deduplication testing
            review_url = f"demo://reviews/{ext_id}" if ext_id else None

            reviews_list.append(RawReviewIn(
                product_name=default_product,
                brand=default_brand,
                external_review_id=ext_id,
                review_title=title,
                raw_review_text=raw_text,
                normalized_review_text=normalized_text,
                rating=rating,
                reviewer_name=author,
                review_date_raw=date_raw,
                source="demo_catalog",
                review_url=review_url,
                helpful_count=helpful_count
            ))

        return reviews_list
