import uuid
from backend.app.models.scraping_job import ScrapingJob
from backend.app.services.job_runner import execute_scraping_job, sanitize_error_message
from backend.app.scrapers.registry import ScraperRegistry
from backend.app.scrapers.base import BaseReviewScraper

def test_job_successful_lifecycle(db_session):
    job_uuid = str(uuid.uuid4())
    job = ScrapingJob(
        job_id=job_uuid,
        target_url="demo://galaxy-s24-ultra",
        scraper_type="demo",
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
        max_pages=1,
        delay_seconds=0.0,
        db_session=db_session
    )

    updated = db_session.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid).first()
    assert updated.status == "COMPLETED"
    assert updated.started_at is not None
    assert updated.finished_at is not None
    assert updated.successful_pages == 1
    assert updated.failed_pages == 0

def test_job_failed_lifecycle_on_fatal_error(db_session):
    # Register a temporary broken scraper to simulate network/unhandled crash
    class CrashingScraper(BaseReviewScraper):
        def validate_url(self, url: str) -> bool:
            return True
        def fetch_page_content(self, url: str, page_num: int) -> str:
            raise ConnectionError("Host unreachable: C:\\Windows\\System32\\fake.dll socket error")
        def parse_page(self, html_content: str, metadata: dict):
            return []

    ScraperRegistry.register("crashing_test", CrashingScraper)

    job_uuid = str(uuid.uuid4())
    job = ScrapingJob(
        job_id=job_uuid,
        target_url="demo://crash",
        scraper_type="crashing_test",
        status="PENDING"
    )
    db_session.add(job)
    db_session.commit()

    execute_scraping_job(
        job_uuid=job_uuid,
        target_url="demo://crash",
        scraper_type="crashing_test",
        max_pages=2,
        delay_seconds=0.0,
        db_session=db_session
    )

    updated = db_session.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid).first()
    # Must NOT remain RUNNING
    assert updated.status == "FAILED"
    assert updated.finished_at is not None
    assert updated.successful_pages == 0
    assert updated.failed_pages == 2
    assert updated.error_log is not None
    # Verify path was sanitized
    assert "C:\\Windows\\System32" not in updated.error_log

def test_sanitize_error_message():
    raw_error = Exception("Error in C:\\Users\\secret\\code\\app.py on line 42")
    sanitized = sanitize_error_message(raw_error)
    assert "C:\\Users\\secret" not in sanitized
    assert "<path>" in sanitized
