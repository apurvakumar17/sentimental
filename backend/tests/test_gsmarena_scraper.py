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
    # Valid opinions URLs
    assert scraper.validate_url("https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php") is True
    assert scraper.validate_url("http://www.gsmarena.com/samsung_galaxy_s24_ultra-reviews-12771p2.php") is True
    # Valid editorial review URLs and review comments
    assert scraper.validate_url("https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php") is True
    assert scraper.validate_url("https://www.gsmarena.com/reviewcomm-2787.php") is True
    assert scraper.validate_url("https://www.gsmarena.com/google_pixel_9_pro-review-2740p3.php") is True
    # Valid offline fixture schemes
    assert scraper.validate_url("gsmarena://sample") is True
    assert scraper.validate_url("gsmarena://fixture-a") is True
    assert scraper.validate_url("gsmarena://fixture-b") is True
    # Invalid domains
    assert scraper.validate_url("https://www.amazon.com/dp/B0CHX1W1XY") is False
    assert scraper.validate_url("https://google.com/search?q=gsmarena") is False
    # Invalid schemes
    assert scraper.validate_url("javascript:alert(1)") is False
    assert scraper.validate_url("file:///local/path/review.html") is False
    # Non-review pages on gsmarena.com
    assert scraper.validate_url("https://www.gsmarena.com/news.php3") is False
    assert scraper.validate_url("https://www.gsmarena.com/glossary.php3") is False
    assert scraper.validate_url("https://www.gsmarena.com/contact.php3") is False

def test_gsmarena_pagination_url_builder():
    scraper = GSMArenaReviewScraper(delay_seconds=0.0)
    # -reviews- pattern
    base_opinions = "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php"
    assert scraper.build_page_url(base_opinions, 1) == base_opinions
    assert scraper.build_page_url(base_opinions, 2) == "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557p2.php"

    # -review- pattern
    base_review = "https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php"
    assert scraper.build_page_url(base_review, 1) == base_review
    assert scraper.build_page_url(base_review, 2) == "https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787p2.php"

    # reviewcomm- pattern
    base_comm = "https://www.gsmarena.com/reviewcomm-2787.php"
    assert scraper.build_page_url(base_comm, 1) == base_comm
    assert scraper.build_page_url(base_comm, 3) == "https://www.gsmarena.com/reviewcomm-2787p3.php"

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

def test_gsmarena_dynamic_multi_fixture_parsing():
    """
    Demonstrates dynamic parsing across different smartphone models without hardcoded logic:
      Fixture A: Samsung Galaxy S25 Ultra
      Fixture B: Google Pixel 9 Pro
    """
    scraper = GSMArenaReviewScraper(delay_seconds=0.0)

    # Fixture A: Samsung Galaxy S25 Ultra
    html_a = (FIXTURES_DIR / "gsmarena_fixture_a.html").read_text(encoding="utf-8")
    reviews_a = scraper.parse_page(html_a, {"target_url": "https://www.gsmarena.com/samsung_galaxy_s25_ultra-review-2787.php"})
    assert len(reviews_a) == 3
    assert reviews_a[0].product_name == "Samsung Galaxy S25 Ultra"
    assert reviews_a[0].brand == "Samsung"
    assert reviews_a[0].external_review_id == "3451001"
    assert "Snapdragon 8 Elite" in reviews_a[0].raw_review_text
    # Quoted reply stripped in review 2
    assert "Alex Tech: The Snapdragon 8 Elite" not in reviews_a[1].raw_review_text
    assert "Agreed on the processor" in reviews_a[1].raw_review_text

    # Fixture B: Google Pixel 9 Pro
    html_b = (FIXTURES_DIR / "gsmarena_fixture_b.html").read_text(encoding="utf-8")
    reviews_b = scraper.parse_page(html_b, {"target_url": "https://www.gsmarena.com/google_pixel_9_pro-review-2740.php"})
    assert len(reviews_b) == 3
    # Suffix 'review' cleanly stripped from 'Google Pixel 9 Pro review'
    assert reviews_b[0].product_name == "Google Pixel 9 Pro"
    assert reviews_b[0].brand == "Google"
    assert reviews_b[0].external_review_id == "5672001"
    assert "PixelFanatic" in reviews_b[0].reviewer_name
    assert "Tensor G4" in reviews_b[1].raw_review_text

def test_gsmarena_metadata_precedence():
    """
    Verifies precedence:
      Explicit user-provided product info -> Page-derived product info -> Safe fallback
    """
    scraper = GSMArenaReviewScraper(delay_seconds=0.0)
    html = (FIXTURES_DIR / "gsmarena_fixture_a.html").read_text(encoding="utf-8")

    # 1. Explicit user metadata overrides page-derived metadata
    reviews_explicit = scraper.parse_page(html, {
        "product_name": "Custom Galaxy S25 Variant",
        "brand": "CustomBrand"
    })
    assert reviews_explicit[0].product_name == "Custom Galaxy S25 Variant"
    assert reviews_explicit[0].brand == "CustomBrand"

    # 2. Page-derived metadata when empty
    reviews_auto = scraper.parse_page(html, {})
    assert reviews_auto[0].product_name == "Samsung Galaxy S25 Ultra"
    assert reviews_auto[0].brand == "Samsung"

    # 3. Fallback when page has no title or h1
    reviews_fallback = scraper.parse_page("<div><div class='user-thread' id='1'><p class='uopin'>Great phone</p></div></div>", {})
    assert reviews_fallback[0].product_name == "Smartphone"
    assert reviews_fallback[0].brand == "Smartphone"

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

def test_gsmarena_custom_phone_job_auto_links_product(db_session):
    """
    Verifies that when a custom GSM Arena phone URL is scraped without explicit product metadata,
    the job runner dynamically derives the product, creates/links it to the job, and saves reviews.
    On a repeat run, the existing product is reused and duplicate reviews are filtered.
    """
    job_uuid_1 = str(uuid.uuid4())
    job_1 = ScrapingJob(
        job_id=job_uuid_1,
        target_url="gsmarena://fixture-a",
        scraper_type="gsmarena",
        status="PENDING"
    )
    db_session.add(job_1)
    db_session.commit()

    # Execute without explicit product_name or brand
    execute_scraping_job(
        job_uuid=job_uuid_1,
        target_url="gsmarena://fixture-a",
        scraper_type="gsmarena",
        product_name=None,
        brand=None,
        max_pages=1,
        max_reviews=10,
        delay_seconds=0.0,
        db_session=db_session
    )

    updated_job_1 = db_session.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid_1).first()
    assert updated_job_1.status == "COMPLETED"
    assert updated_job_1.product_id is not None
    derived_product = db_session.query(Product).filter(Product.id == updated_job_1.product_id).first()
    assert derived_product.name == "Samsung Galaxy S25 Ultra"
    assert derived_product.brand == "Samsung"
    assert updated_job_1.inserted_reviews == 3
    assert updated_job_1.duplicate_reviews == 0

    # Second run with same fixture: verifies product reuse and deduplication
    job_uuid_2 = str(uuid.uuid4())
    job_2 = ScrapingJob(
        job_id=job_uuid_2,
        target_url="gsmarena://fixture-a",
        scraper_type="gsmarena",
        status="PENDING"
    )
    db_session.add(job_2)
    db_session.commit()

    execute_scraping_job(
        job_uuid=job_uuid_2,
        target_url="gsmarena://fixture-a",
        scraper_type="gsmarena",
        product_name=None,
        brand=None,
        max_pages=1,
        max_reviews=10,
        delay_seconds=0.0,
        db_session=db_session
    )

    updated_job_2 = db_session.query(ScrapingJob).filter(ScrapingJob.job_id == job_uuid_2).first()
    assert updated_job_2.status == "COMPLETED"
    assert updated_job_2.product_id == derived_product.id  # Reused same product
    assert updated_job_2.inserted_reviews == 0
    assert updated_job_2.duplicate_reviews == 3

def test_gsmarena_has_next_page_pagination_detection():
    """
    Verifies that GSMArenaReviewScraper accurately detects next pages across:
    - User opinion pagination widget (#nav-review-page-temp with span.count of N)
    - Forward gallery arrow icons
    - Editorial review 'next-page' anchors
    - Terminal / disabled states
    """
    scraper = GSMArenaReviewScraper()

    # 1. Sample fixture has 'of 18' pages
    sample_html = scraper.fetch_page_content("gsmarena://sample", 1)
    assert scraper.has_next_page(sample_html, 1) is True
    assert scraper.has_next_page(sample_html, 18) is False

    # 2. Editorial next page button
    editorial_html = '<div><a class="next-page" href="phone-review-123p2.php">Next Page</a></div>'
    assert scraper.has_next_page(editorial_html, 1) is True

    # 3. Arrow icon button
    arrow_html = '<div id="nav-review-page-temp"><a class="prevnextbutton" href="phone-reviews-123p2.php"><i class="head-icon icon-gallery-arrow-right"></i></a></div>'
    assert scraper.has_next_page(arrow_html, 1) is True

    # 4. Arrow icon disabled (last page)
    arrow_disabled = '<div id="nav-review-page-temp"><a class="prevnextbutton disabled" href="#"><i class="head-icon icon-gallery-arrow-right"></i></a></div>'
    assert scraper.has_next_page(arrow_disabled, 1) is False

    # 5. Single-page fixture without pagination
    fixture_a_html = scraper.fetch_page_content("gsmarena://fixture-a", 1)
    assert scraper.has_next_page(fixture_a_html, 1) is False

