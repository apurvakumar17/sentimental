import uuid
from pathlib import Path
from backend.app.scrapers.gsmarena_scraper import GSMArenaReviewScraper
from backend.app.scrapers.registry import ScraperRegistry
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.scraping_job import ScrapingJob
from backend.app.services.ingestion import ingest_review_batch
from backend.app.services.job_runner import execute_scraping_job

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "scrapers" / "fixtures"

def test_gsmarena_scraper_registered():
    scraper_cls = ScraperRegistry.get("gsmarena")
    assert scraper_cls == GSMArenaReviewScraper
    assert "gsmarena" in ScraperRegistry.available_scrapers()

def test_gsmarena_url_validation():
    scraper = GSMArenaReviewScraper(delay_seconds=0.0)
    assert scraper.validate_url("https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php") is True
    assert scraper.validate_url("http://www.gsmarena.com/samsung_galaxy_s24_ultra-reviews-12771p2.php") is True
    assert scraper.validate_url("gsmarena://sample") is True
    assert scraper.validate_url("https://www.amazon.com/dp/B0CHX1W1XY") is False
    assert scraper.validate_url("https://gsmarena.com/news.php") is False  # not a reviews page

def test_gsmarena_pagination_url_builder():
    scraper = GSMArenaReviewScraper(delay_seconds=0.0)
    base = "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php"
    assert scraper.build_page_url(base, 1) == base
    assert scraper.build_page_url(base, 2) == "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557p2.php"
    assert scraper.build_page_url(base, 5) == "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557p5.php"

    # Preserves p2 when passed as base
    p2_base = "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557p2.php"
    assert scraper.build_page_url(p2_base, 3) == "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557p3.php"
    assert scraper.build_page_url(p2_base, 1) == "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php"

def test_gsmarena_parse_representative_fixture():
    scraper = GSMArenaReviewScraper(delay_seconds=0.0)
    html = (FIXTURES_DIR / "gsmarena_sample.html").read_text(encoding="utf-8")
    reviews = scraper.parse_page(html, {
        "product_name": "Apple iPhone 15 Pro",
        "brand": "Apple",
        "target_url": "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php"
    })

    assert len(reviews) > 0
    first = reviews[0]
    assert first.product_name == "Apple iPhone 15 Pro"
    assert first.brand == "Apple"
    assert first.source == "gsmarena"
    assert first.external_review_id == "7070559"
    assert first.reviewer_name == "Anonymous"
    assert "05 Aug 2026" in first.review_date_raw
    assert "Even 450 euro is a great deal in Europe now" in first.raw_review_text
    # Quoted reply span must have been stripped from review body
    assert "Not worth at that price unless" not in first.raw_review_text
    assert first.review_url == "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php#7070559"

def test_gsmarena_parse_malformed_fixture():
    scraper = GSMArenaReviewScraper(delay_seconds=0.0)
    html = (FIXTURES_DIR / "gsmarena_malformed.html").read_text(encoding="utf-8")
    reviews = scraper.parse_page(html, {"product_name": "Test Phone"})

    # Valid thread parsed, empty thread dropped, thread without author/id handled cleanly
    assert len(reviews) == 2
    assert reviews[0].external_review_id == "9999001"
    assert reviews[0].reviewer_name == "TechReviewer99"
    assert "Outstanding camera performance" in reviews[0].raw_review_text

    assert reviews[1].external_review_id is None
    assert reviews[1].reviewer_name == "Anonymous"
    assert "Decent battery life" in reviews[1].raw_review_text

def test_gsmarena_ingestion_and_repeated_deduplication(db_session):
    """
    End-to-End Ingestion + Deduplication:
    First run inserts reviews.
    Second run on identical source inserts 0 reviews and flags all as duplicates.
    """
    prod = Product(name="Apple iPhone 15 Pro", brand="Apple")
    job1 = ScrapingJob(target_url="gsmarena://sample", scraper_type="gsmarena", status="RUNNING")
    db_session.add_all([prod, job1])
    db_session.commit()

    scraper = GSMArenaReviewScraper(delay_seconds=0.0)
    html = (FIXTURES_DIR / "gsmarena_sample.html").read_text(encoding="utf-8")
    extracted_reviews = scraper.parse_page(html, {
        "product_name": prod.name,
        "brand": prod.brand,
        "target_url": "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php"
    })

    # Run 1: All reviews inserted
    ins1, dups1 = ingest_review_batch(db_session, extracted_reviews, job1, default_product_id=prod.id)
    assert ins1 == len(extracted_reviews)
    assert dups1 == 0
    count_after_run1 = db_session.query(Review).filter(Review.product_id == prod.id).count()
    assert count_after_run1 == ins1

    # Run 2: Exact same reviews repeated on a new job
    job2 = ScrapingJob(target_url="gsmarena://sample", scraper_type="gsmarena", status="RUNNING")
    db_session.add(job2)
    db_session.commit()

    ins2, dups2 = ingest_review_batch(db_session, extracted_reviews, job2, default_product_id=prod.id)
    assert ins2 == 0
    assert dups2 == len(extracted_reviews)

    # Database total count must NOT have increased
    count_after_run2 = db_session.query(Review).filter(Review.product_id == prod.id).count()
    assert count_after_run2 == count_after_run1

def test_gsmarena_job_runner_lifecycle(db_session):
    """
    Verifies that the GSM Arena adapter executes end-to-end through the background job runner.
    """
    job_uuid = str(uuid.uuid4())
    job = ScrapingJob(
        job_id=job_uuid,
        target_url="gsmarena://sample",
        scraper_type="gsmarena",
        status="PENDING"
    )
    db_session.add(job)
    db_session.commit()

    execute_scraping_job(
        job_uuid=job_uuid,
        target_url="gsmarena://sample",
        scraper_type="gsmarena",
        product_name="Apple iPhone 15 Pro",
        brand="Apple",
        max_pages=1,
        max_reviews=5,
        delay_seconds=0.0,
        db_session=db_session
    )

    updated_job = db_session.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid).first()
    assert updated_job.status == "COMPLETED"
    assert updated_job.pages_attempted == 1
    assert updated_job.successful_pages == 1
    assert updated_job.inserted_reviews <= 5
    assert updated_job.reviews_discovered > 0
