import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.scraping_job import ScrapingJob
from backend.app.scrapers.registry import ScraperRegistry
from backend.app.services.ingestion import ingest_review_batch, get_or_create_product

logger = logging.getLogger("smartreview.job_runner")

def sanitize_error_message(exc: Exception) -> str:
    """Produces a clean, user-safe error summary without leaking internal system paths."""
    err_str = str(exc)
    # Remove file paths if present
    import re
    cleaned = re.sub(r"[a-zA-Z]:\\[^\s]+", "<path>", err_str)
    cleaned = re.sub(r"/home/[^\s]+", "<path>", cleaned)
    return cleaned[:500]

def execute_scraping_job(
    job_uuid: str,
    target_url: str,
    scraper_type: str,
    product_name: Optional[str] = None,
    brand: Optional[str] = None,
    max_pages: int = 3,
    max_reviews: Optional[int] = None,
    delay_seconds: float = 1.0,
    db_session: Optional[Session] = None
):
    """
    Background worker function to execute a single scraping job.
    Guarantees deterministic lifecycle transitions:
      PENDING -> RUNNING -> COMPLETED
      or
      PENDING -> RUNNING -> FAILED
    Ensures jobs never remain stuck in RUNNING on uncaught exceptions.
    """
    close_db_when_done = False
    if db_session is not None:
        db = db_session
    else:
        db = SessionLocal()
        close_db_when_done = True

    try:
        job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid).first()
        if not job:
            logger.error(f"Job {job_uuid} not found in database")
            return

        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        job.max_pages = max_pages
        job.max_reviews = max_reviews
        db.commit()

        # Link product if name provided
        default_prod_id = None
        if product_name:
            prod = get_or_create_product(db, name=product_name, brand=brand)
            job.product_id = prod.id
            default_prod_id = prod.id
            db.commit()

        scraper_cls = ScraperRegistry.get(scraper_type)
        scraper_instance = scraper_cls(delay_seconds=delay_seconds)

        meta = {
            "product_name": product_name,
            "brand": brand
        }

        errors = []
        for batch_result in scraper_instance.scrape(
            target_url,
            max_pages=max_pages,
            max_reviews=max_reviews,
            metadata=meta
        ):
            job.pages_attempted += 1
            if batch_result["success"]:
                job.successful_pages += 1
                batch_reviews = batch_result["reviews"]
                job.reviews_discovered += len(batch_reviews)

                remaining = (max_reviews - job.inserted_reviews) if max_reviews else None
                ins, dups = ingest_review_batch(
                    db,
                    batch_reviews,
                    job,
                    default_product_id=default_prod_id,
                    max_reviews_remaining=remaining
                )
                job.inserted_reviews += ins
                job.duplicate_reviews += dups
            else:
                job.failed_pages += 1
                if batch_result["error"]:
                    errors.append(f"Page {batch_result['page']}: {sanitize_error_message(batch_result['error'])}")

            db.commit()

            # Early break if max_reviews cap hit
            if max_reviews and job.inserted_reviews >= max_reviews:
                break

        if errors:
            job.error_log = "\n".join(errors)

        # Final status evaluation
        if job.successful_pages > 0:
            job.status = "COMPLETED"
        else:
            job.status = "FAILED"
            if not job.error_log:
                job.error_log = "All page fetch attempts failed."

        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Job {job_uuid} finished with status={job.status}")

    except Exception as exc:
        logger.error(f"Job {job_uuid} crashed with error: {exc}", exc_info=True)
        try:
            job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid).first()
            if job:
                job.status = "FAILED"
                job.error_log = sanitize_error_message(exc)
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as commit_exc:
            logger.error(f"Failed to record failure status for job {job_uuid}: {commit_exc}")
    finally:
        if close_db_when_done:
            db.close()
