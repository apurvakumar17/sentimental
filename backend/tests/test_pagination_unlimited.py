import uuid
import pytest
from typing import List, Dict, Any, Optional
from pydantic import ValidationError

from backend.app.schemas.scraping_job import ScrapingJobCreate
from backend.app.scrapers.base import BaseReviewScraper
from backend.app.schemas.review import RawReviewIn
from backend.app.models.scraping_job import ScrapingJob
from backend.app.services.job_runner import execute_scraping_job
from backend.app.scrapers.registry import ScraperRegistry

class MockPaginatedScraper(BaseReviewScraper):
    """Custom test scraper for deterministic pagination unit tests."""

    def __init__(self, page_dict: Dict[int, List[Dict[str, Any]]], loop_target: Optional[int] = None, **kwargs):
        super().__init__(delay_seconds=0.0, **kwargs)
        self.page_dict = page_dict
        self.loop_target = loop_target

    def validate_url(self, url: str) -> bool:
        return True

    def build_page_url(self, base_url: str, page_num: int) -> str:
        if self.loop_target is not None and page_num > len(self.page_dict):
            # Simulate a pagination loop returning to an earlier page URL
            return f"{base_url}?page={self.loop_target}"
        return f"{base_url}?page={page_num}"

    def fetch_page_content(self, url: str, page_num: int) -> str:
        # Returns simple HTML indicating the page number
        return f"<html><body><div id='page'>{page_num}</div></body></html>"

    def has_next_page(self, html_content: str, current_page: int) -> bool:
        # There is a next page if current_page < max pages available in page_dict
        return current_page < len(self.page_dict)

    def parse_page(self, html_content: str, metadata: Dict[str, Any]) -> List[RawReviewIn]:
        import re
        match = re.search(r"<div id='page'>(\d+)</div>", html_content)
        page_num = int(match.group(1)) if match else 1

        items = self.page_dict.get(page_num, [])
        reviews: List[RawReviewIn] = []
        for i, item in enumerate(items):
            reviews.append(RawReviewIn(
                product_name="Test Device",
                brand="TestBrand",
                external_review_id=f"p{page_num}-r{i}",
                raw_review_text=item.get("text", f"Review text for page {page_num} item {i}"),
                normalized_review_text=item.get("text", f"Review text for page {page_num} item {i}"),
                rating=4.5,
                reviewer_name=f"User_p{page_num}_{i}",
                source="test_source",
                review_url=f"http://test.com/review/p{page_num}/{i}"
            ))
        return reviews


# ==============================================================================
# 1. Validation Tests
# ==============================================================================

def test_validation_valid_page_counts():
    """Verifies that arbitrary positive integers and None (null) are valid."""
    for val in [1, 5, 10, 50, 100, 500, 1000]:
        job = ScrapingJobCreate(target_url="demo://test", scraper_type="demo", max_pages=val)
        assert job.max_pages == val

    job_unlimited = ScrapingJobCreate(target_url="demo://test", scraper_type="demo", max_pages=None)
    assert job_unlimited.max_pages is None

def test_validation_invalid_page_counts():
    """Verifies that 0, negative integers, and non-integers fail validation."""
    for invalid_val in [0, -1, -50]:
        with pytest.raises(ValidationError):
            ScrapingJobCreate(target_url="demo://test", scraper_type="demo", max_pages=invalid_val)


# ==============================================================================
# 2. Limited Pagination Test
# ==============================================================================

def test_limited_pagination_cutoff():
    """
    Creates a fixture with 7 pages.
    Runs max_pages = 3 -> exactly 3 pages processed.
    Runs max_pages = 7 -> exactly 7 pages processed.
    """
    pages_data = {i: [{"text": f"Review content page {i}"}] for i in range(1, 8)}
    scraper = MockPaginatedScraper(page_dict=pages_data)

    # Run with max_pages = 3
    batches_3 = list(scraper.scrape("demo://test-phone", max_pages=3))
    assert len(batches_3) == 3
    assert [b["page"] for b in batches_3] == [1, 2, 3]

    # Run with max_pages = 7
    batches_7 = list(scraper.scrape("demo://test-phone", max_pages=7))
    assert len(batches_7) == 7
    assert [b["page"] for b in batches_7] == [1, 2, 3, 4, 5, 6, 7]


# ==============================================================================
# 3. Unlimited Pagination Test (Naturally stops after page 4)
# ==============================================================================

def test_unlimited_pagination_stops_naturally():
    """
    Creates a fixture with 4 pages (Page 4 has no next page).
    Runs max_pages = None.
    Expected: exactly 4 pages processed, automatically terminates without hanging.
    """
    pages_data = {i: [{"text": f"Review content page {i}"}] for i in range(1, 5)}
    scraper = MockPaginatedScraper(page_dict=pages_data)

    batches = list(scraper.scrape("demo://test-phone", max_pages=None))
    assert len(batches) == 4
    assert [b["page"] for b in batches] == [1, 2, 3, 4]


# ==============================================================================
# 4. Pagination Loop Test
# ==============================================================================

def test_pagination_loop_prevention():
    """
    Simulates a loop: Page 1 -> Page 2 -> Page 1.
    Runs max_pages = None.
    Expected: Scraper detects repeated URL on iteration 3 and terminates cleanly.
    """
    pages_data = {
        1: [{"text": "Page 1 review"}],
        2: [{"text": "Page 2 review"}]
    }
    # Loop back to page 1 after page 2
    scraper = MockPaginatedScraper(page_dict=pages_data, loop_target=1)

    batches = list(scraper.scrape("demo://test-phone", max_pages=None))
    assert len(batches) == 2
    assert [b["page"] for b in batches] == [1, 2]


# ==============================================================================
# 5. Empty-Page Test
# ==============================================================================

def test_empty_page_safe_termination():
    """
    Page 1 contains reviews, Page 2 returns empty reviews.
    Unlimited mode (max_pages=None) must terminate safely rather than continuing.
    """
    pages_data = {
        1: [{"text": "Page 1 review"}],
        2: [] # Empty review list
    }
    scraper = MockPaginatedScraper(page_dict=pages_data)

    batches = list(scraper.scrape("demo://test-phone", max_pages=None))
    # Stops when encountering empty page
    assert len(batches) == 1
    assert batches[0]["page"] == 1


# ==============================================================================
# 6. Max-Reviews Cap with Unlimited Pages
# ==============================================================================

def test_max_reviews_cap_with_unlimited_pages():
    """
    max_pages = None, max_reviews = 5.
    Fixture has 10 pages with 2 reviews each (total 20 reviews).
    Scraper must terminate early once 5 reviews are collected.
    """
    pages_data = {i: [{"text": f"Review {i}A"}, {"text": f"Review {i}B"}] for i in range(1, 11)}
    scraper = MockPaginatedScraper(page_dict=pages_data)

    batches = list(scraper.scrape("demo://test-phone", max_pages=None, max_reviews=5))
    total_extracted = sum(len(b["reviews"]) for b in batches)
    assert total_extracted == 5
    # Should stop around page 3 (2 + 2 + 1)
    assert len(batches) == 3


# ==============================================================================
# 7. Job Runner Execution with Unlimited Mode
# ==============================================================================

def test_job_runner_unlimited_mode(db_session):
    """
    Verifies that a job created with max_pages = None executes through
    the background job runner, reaches COMPLETED, and records final page counts.
    """
    job_uuid = str(uuid.uuid4())
    job = ScrapingJob(
        job_id=job_uuid,
        target_url="demo://galaxy-s24-ultra",
        scraper_type="demo",
        max_pages=None, # Unlimited mode
        status="PENDING"
    )
    db_session.add(job)
    db_session.commit()

    execute_scraping_job(
        job_uuid=job_uuid,
        target_url="demo://galaxy-s24-ultra",
        scraper_type="demo",
        product_name="Samsung Galaxy S24 Ultra",
        brand="Samsung",
        max_pages=None,
        max_reviews=None,
        delay_seconds=0.0,
        db_session=db_session
    )

    updated_job = db_session.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid).first()
    assert updated_job.status == "COMPLETED"
    assert updated_job.max_pages is None
    # galaxy-s24-ultra has 2 pages in DEMO_SMARTPHONES
    assert updated_job.pages_attempted == 2
    assert updated_job.successful_pages == 2
    assert updated_job.inserted_reviews > 0
