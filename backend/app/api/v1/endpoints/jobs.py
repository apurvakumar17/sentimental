import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.scraping_job import ScrapingJob
from backend.app.schemas.scraping_job import ScrapingJobCreate, ScrapingJobResponse, ScrapingJobListResponse
from backend.app.scrapers.registry import ScraperRegistry
from backend.app.services.job_runner import execute_scraping_job

router = APIRouter()

@router.post("/scrape", response_model=ScrapingJobResponse, status_code=202)
def trigger_scrape_job(
    job_in: ScrapingJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Upfront validation of scraper type against registry
    available = ScraperRegistry.available_scrapers()
    if job_in.scraper_type.lower() not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported scraper type '{job_in.scraper_type}'. Available adapters: {available}"
        )

    job_uuid = str(uuid.uuid4())
    job = ScrapingJob(
        job_id=job_uuid,
        target_url=job_in.target_url,
        scraper_type=job_in.scraper_type.lower(),
        max_pages=job_in.max_pages,
        max_reviews=job_in.max_reviews,
        status="PENDING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch to background worker
    background_tasks.add_task(
        execute_scraping_job,
        job_uuid=job_uuid,
        target_url=job_in.target_url,
        scraper_type=job_in.scraper_type.lower(),
        product_name=job_in.product_name,
        brand=job_in.brand,
        max_pages=job_in.max_pages,
        max_reviews=job_in.max_reviews,
        delay_seconds=job_in.delay_seconds
    )

    return ScrapingJobResponse(
        id=job.id,
        job_id=job.job_id,
        target_url=job.target_url,
        scraper_type=job.scraper_type,
        product_id=job.product_id,
        product_name=job_in.product_name,
        status=job.status,
        max_pages=job.max_pages,
        max_reviews=job.max_reviews,
        pages_attempted=job.pages_attempted,
        successful_pages=job.successful_pages,
        failed_pages=job.failed_pages,
        reviews_discovered=job.reviews_discovered,
        inserted_reviews=job.inserted_reviews,
        duplicate_reviews=job.duplicate_reviews,
        error_log=job.error_log,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at
    )

@router.get("", response_model=ScrapingJobListResponse)
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, RUNNING, COMPLETED, FAILED)"),
    db: Session = Depends(get_db)
):
    query = db.query(ScrapingJob)
    if status:
        query = query.filter(ScrapingJob.status == status.upper())

    jobs = query.order_by(ScrapingJob.id.desc()).all()
    items = []
    for j in jobs:
        items.append(ScrapingJobResponse(
            id=j.id,
            job_id=j.job_id,
            target_url=j.target_url,
            scraper_type=j.scraper_type,
            product_id=j.product_id,
            product_name=j.product.name if j.product else None,
            status=j.status,
            max_pages=j.max_pages,
            max_reviews=j.max_reviews,
            pages_attempted=j.pages_attempted,
            successful_pages=j.successful_pages,
            failed_pages=j.failed_pages,
            reviews_discovered=j.reviews_discovered,
            inserted_reviews=j.inserted_reviews,
            duplicate_reviews=j.duplicate_reviews,
            error_log=j.error_log,
            started_at=j.started_at,
            finished_at=j.finished_at,
            created_at=j.created_at
        ))

    return ScrapingJobListResponse(
        total=len(items),
        items=items
    )

@router.get("/{job_identifier}", response_model=ScrapingJobResponse)
def get_job(job_identifier: str, db: Session = Depends(get_db)):
    if job_identifier.isdigit():
        job = db.query(ScrapingJob).filter(ScrapingJob.id == int(job_identifier)).first()
    else:
        job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_identifier).first()

    if not job:
        raise HTTPException(status_code=404, detail="Scraping job not found")

    return ScrapingJobResponse(
        id=job.id,
        job_id=job.job_id,
        target_url=job.target_url,
        scraper_type=job.scraper_type,
        product_id=job.product_id,
        product_name=job.product.name if job.product else None,
        status=job.status,
        max_pages=job.max_pages,
        max_reviews=job.max_reviews,
        pages_attempted=job.pages_attempted,
        successful_pages=job.successful_pages,
        failed_pages=job.failed_pages,
        reviews_discovered=job.reviews_discovered,
        inserted_reviews=job.inserted_reviews,
        duplicate_reviews=job.duplicate_reviews,
        error_log=job.error_log,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at
    )
