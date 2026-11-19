import uuid
import re
from pathlib import Path
import pytest
from bs4 import BeautifulSoup

from backend.app.scrapers.flipkart_scraper import (
    FlipkartReviewScraper,
    FlipkartChallengeError,
    is_flipkart_challenge
)
from backend.app.scrapers.registry import ScraperRegistry
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.scraping_job import ScrapingJob
from backend.app.services.job_runner import execute_scraping_job

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "scrapers" / "fixtures"


def test_flipkart_scraper_registered():
    scraper_cls = ScraperRegistry.get("flipkart")
    assert scraper_cls == FlipkartReviewScraper
    assert "flipkart" in ScraperRegistry.available_scrapers()


def test_flipkart_url_validation():
    scraper = FlipkartReviewScraper(delay_seconds=0.0)

    # Valid product review URLs
    assert scraper.validate_url("https://www.flipkart.com/apple-iphone-15-black-128-gb/product-reviews/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W") is True
    assert scraper.validate_url("http://www.flipkart.com/samsung-galaxy-s24-ultra/product-reviews/itm1234?pid=MOB1234&page=2") is True
    assert scraper.validate_url("https://dl.flipkart.com/realme-12-pro/product-reviews/itm5678?pid=MOB5678") is True

    # Valid main product URLs
    assert scraper.validate_url("https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4") is True

    # Valid offline fixture schemes
    assert scraper.validate_url("flipkart://sample") is True
    assert scraper.validate_url("flipkart://challenge") is True

    # Invalid domains
    assert scraper.validate_url("https://www.amazon.in/dp/B0CHX1W1XY") is False
    assert scraper.validate_url("https://www.gsmarena.com/apple_iphone_15-reviews-12557.php") is False
    assert scraper.validate_url("https://google.com/search?q=flipkart") is False

    # Invalid schemes
    assert scraper.validate_url("javascript:alert(1)") is False
    assert scraper.validate_url("file:///local/path/review.html") is False

    # Empty or malformed
    assert scraper.validate_url("") is False
    assert scraper.validate_url("not_a_url") is False


def test_flipkart_pagination_url_builder():
    scraper = FlipkartReviewScraper(delay_seconds=0.0)

    base = "https://www.flipkart.com/apple-iphone-15-black-128-gb/product-reviews/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W"
    # Page 1 should not have page=1 added if not present
    url_p1 = scraper.build_page_url(base, 1)
    assert "page=" not in url_p1
    assert "pid=MOBGTAGPTB3VS24W" in url_p1

    # Page 2 should include page=2
    url_p2 = scraper.build_page_url(base, 2)
    assert "page=2" in url_p2
    assert "pid=MOBGTAGPTB3VS24W" in url_p2

    # Conversion of /p/ to /product-reviews/
    prod_url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W"
    converted = scraper.build_page_url(prod_url, 2)
    assert "/product-reviews/" in converted
    assert "/p/" not in converted
    assert "page=2" in converted

    # Fixture scheme
    fixture_url = "flipkart://sample"
    assert scraper.build_page_url(fixture_url, 3) == "flipkart://sample?page=3"


def test_flipkart_parse_sample_fixture():
    scraper = FlipkartReviewScraper(delay_seconds=0.0)
    fixture_path = FIXTURES_DIR / "flipkart_sample.html"
    assert fixture_path.exists(), "flipkart_sample.html must exist"

    html = fixture_path.read_text(encoding="utf-8")
    reviews = scraper.parse_page(html, {
        "target_url": "https://www.flipkart.com/apple-iphone-15-black-128-gb/product-reviews/itm6ac6485515ae4?pid=MOBGTAGPTB3VS24W"
    })

    assert len(reviews) == 10
    first = reviews[0]

    # Inferred product name and brand
    assert first.product_name == "Apple Iphone 15 Black 128 Gb"
    assert first.brand == "Apple"

    # Review details
    assert first.external_review_id == "ef19cdba-2cd2-4957-a285-e4a954f2f5ba"
    assert first.reviewer_name == "Khushboo Verma"
    assert first.rating == 5.0
    assert first.review_title == "Super!"
    assert "Great experience" in first.raw_review_text
    assert first.source == "flipkart"
    assert first.normalized_review_text is not None


def test_flipkart_dom_fallback_extraction():
    scraper = FlipkartReviewScraper(delay_seconds=0.0)
    fixture_path = FIXTURES_DIR / "flipkart_sample.html"
    raw_html = fixture_path.read_text(encoding="utf-8")

    # Disable __INITIAL_STATE__ to force fallback to DOM parsing
    stripped_html = raw_html.replace("window.__INITIAL_STATE__", "window.__DISABLED_STATE__")
    assert "window.__INITIAL_STATE__" not in stripped_html

    reviews = scraper.parse_page(stripped_html, {
        "product_name": "Apple iPhone 15",
        "brand": "Apple",
        "target_url": "https://www.flipkart.com/apple-iphone-15-black-128-gb/product-reviews/itm6ac6485515ae4"
    })

    assert len(reviews) > 0
    first = reviews[0]
    assert first.product_name == "Apple iPhone 15"
    assert first.rating is not None
    assert len(first.raw_review_text) > 5


def test_flipkart_has_next_page():
    scraper = FlipkartReviewScraper(delay_seconds=0.0)
    fixture_path = FIXTURES_DIR / "flipkart_sample.html"
    html = fixture_path.read_text(encoding="utf-8")

    # Sample fixture contains hasMorePages: True in state
    assert scraper.has_next_page(html, 1) is True

    # Empty content should return False
    assert scraper.has_next_page("", 1) is False


def test_flipkart_challenge_detection():
    # 403 / 429 status codes
    assert is_flipkart_challenge(403, "Forbidden") is True
    assert is_flipkart_challenge(429, "Too Many Requests") is True

    # Challenge content markers
    assert is_flipkart_challenge(200, "<html><title>Access Denied</title>Blocked by PerimeterX</html>") is True
    assert is_flipkart_challenge(200, "Please verify you are a human before accessing flipkart") is True

    # Normal content
    assert is_flipkart_challenge(200, "<html><head><title>Apple iPhone 15 Reviews</title></head></html>") is False

    # Challenge fixture loading
    scraper = FlipkartReviewScraper(delay_seconds=0.0)
    with pytest.raises(FlipkartChallengeError):
        scraper.fetch_page_content("flipkart://challenge", 1)


def test_flipkart_job_execution(db_session):
    """
    End-to-end integration test: execute a background scraping job with flipkart:// scheme,
    verifying database persistence, product association, and clean status completion.
    """
    job_uuid = str(uuid.uuid4())
    job = ScrapingJob(
        job_id=job_uuid,
        target_url="flipkart://sample",
        scraper_type="flipkart",
        status="PENDING",
        max_pages=1,
        max_reviews=10
    )
    db_session.add(job)
    db_session.commit()

    execute_scraping_job(
        job_uuid=job_uuid,
        target_url="flipkart://sample",
        scraper_type="flipkart",
        product_name="Apple iPhone 15",
        brand="Apple",
        max_pages=1,
        max_reviews=10,
        delay_seconds=0.0,
        db_session=db_session
    )

    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.reviews_discovered == 10
    assert job.inserted_reviews == 10
    assert job.failed_pages == 0

    # Verify reviews persisted in db
    reviews = db_session.query(Review).filter(Review.scraping_job_id == job.id).all()
    assert len(reviews) == 10
    assert any("Great experience" in r.raw_review_text for r in reviews)
