import pytest
from backend.app.scrapers.demo_scraper import DemoReviewScraper, DEMO_SMARTPHONES
from backend.app.scrapers.registry import ScraperRegistry

def test_scraper_registry():
    scraper_cls = ScraperRegistry.get("demo")
    assert scraper_cls == DemoReviewScraper

    with pytest.raises(ValueError):
        ScraperRegistry.get("non_existent_scraper")

def test_demo_scraper_url_validation():
    scraper = DemoReviewScraper(delay_seconds=0.0)
    assert scraper.validate_url("demo://iphone-15-pro") is True
    assert scraper.validate_url("http://mock-reviews.com/phones") is True
    assert scraper.validate_url("https://unsupported-random-site.xyz") is False

def test_demo_scraper_page_parsing():
    scraper = DemoReviewScraper(delay_seconds=0.0)
    html = scraper.fetch_page_content("demo://iphone-15-pro", page_num=1)
    assert "<title>" in html
    assert "iPhone 15 Pro" in html

    reviews = scraper.parse_page(html, {"product_name": "Apple iPhone 15 Pro", "brand": "Apple"})
    assert len(reviews) > 0

    first = reviews[0]
    assert first.product_name == "Apple iPhone 15 Pro"
    assert first.brand == "Apple"
    assert first.rating is not None
    assert len(first.raw_review_text) > 10
    assert first.source == "demo_catalog"

def test_demo_scraper_multipage_run():
    scraper = DemoReviewScraper(delay_seconds=0.0)
    batches = list(scraper.scrape("demo://galaxy-s24-ultra", max_pages=2))

    assert len(batches) == 2
    assert batches[0]["success"] is True
    assert len(batches[0]["reviews"]) > 0
    assert batches[1]["success"] is True
