from backend.app.models.product import Product
from backend.app.models.scraping_job import ScrapingJob
from backend.app.models.review import Review
from backend.app.schemas.review import RawReviewIn
from backend.app.services.ingestion import ingest_review_batch

def test_tier_1_deduplication_by_external_id(db_session):
    """
    Tier 1: Reviews with identical external_review_id for the same product and source
    must be recognized as duplicates even if the body text has minor modifications.
    """
    prod = Product(name="Pixel 8 Pro", brand="Google")
    job = ScrapingJob(target_url="demo://pixel", scraper_type="demo", status="RUNNING")
    db_session.add_all([prod, job])
    db_session.commit()

    rev1 = RawReviewIn(
        product_name="Pixel 8 Pro",
        external_review_id="ext-rev-100",
        raw_review_text="Initial impression: Screen is vivid and bright.",
        source="tech_blog"
    )
    rev1_edit = RawReviewIn(
        product_name="Pixel 8 Pro",
        external_review_id="ext-rev-100",  # Same external ID
        raw_review_text="Updated impression: Screen is vivid and bright with high nits.",
        source="tech_blog"
    )

    ins, dups = ingest_review_batch(db_session, [rev1, rev1_edit], job, default_product_id=prod.id)
    assert ins == 1
    assert dups == 1

def test_tier_2_deduplication_by_review_url(db_session):
    """
    Tier 2: Reviews with identical review_url for the same product
    must be recognized as duplicates even if external_review_id is absent.
    """
    prod = Product(name="iPhone 15 Pro", brand="Apple")
    job = ScrapingJob(target_url="demo://iphone", scraper_type="demo", status="RUNNING")
    db_session.add_all([prod, job])
    db_session.commit()

    rev1 = RawReviewIn(
        product_name="iPhone 15 Pro",
        review_url="https://reviews.example.com/item/42",
        raw_review_text="Love the lightweight titanium frame.",
        source="web_review"
    )
    rev2_same_url = RawReviewIn(
        product_name="iPhone 15 Pro",
        review_url="https://reviews.example.com/item/42",  # Same URL
        raw_review_text="Titanium frame feels noticeably lighter in hand.",
        source="web_review"
    )

    ins, dups = ingest_review_batch(db_session, [rev1, rev2_same_url], job, default_product_id=prod.id)
    assert ins == 1
    assert dups == 1

def test_tier_3_deduplication_by_deterministic_content_hash(db_session):
    """
    Tier 3 Fallback: When neither external_id nor review_url are provided,
    exact normalized text + product + source match must deduplicate.
    """
    prod = Product(name="Galaxy S24", brand="Samsung")
    job = ScrapingJob(target_url="demo://s24", scraper_type="demo", status="RUNNING")
    db_session.add_all([prod, job])
    db_session.commit()

    rev1 = RawReviewIn(
        product_name="Galaxy S24",
        raw_review_text="Superb display with anti-reflective glass.",
        source="store_a"
    )
    rev2_duplicate = RawReviewIn(
        product_name="Galaxy S24",
        raw_review_text="   Superb display with   anti-reflective glass.  ",
        source="store_a"
    )

    ins, dups = ingest_review_batch(db_session, [rev1, rev2_duplicate], job, default_product_id=prod.id)
    assert ins == 1
    assert dups == 1

def test_distinct_reviews_remain_distinct(db_session):
    """
    Legitimate distinct reviews for the same product must never collide.
    """
    prod = Product(name="Galaxy S24", brand="Samsung")
    job = ScrapingJob(target_url="demo://s24", scraper_type="demo", status="RUNNING")
    db_session.add_all([prod, job])
    db_session.commit()

    rev_a = RawReviewIn(product_name="Galaxy S24", raw_review_text="Battery easily lasts 2 days.", rating=5.0)
    rev_b = RawReviewIn(product_name="Galaxy S24", raw_review_text="Camera zoom at 10x is very clear.", rating=4.5)

    ins, dups = ingest_review_batch(db_session, [rev_a, rev_b], job, default_product_id=prod.id)
    assert ins == 2
    assert dups == 0

def test_identical_text_for_different_products_are_independent(db_session):
    """
    Identical review text across different smartphone models must NOT collide.
    """
    prod1 = Product(name="Phone A", brand="Brand A")
    prod2 = Product(name="Phone B", brand="Brand B")
    job = ScrapingJob(target_url="demo://catalog", scraper_type="demo", status="RUNNING")
    db_session.add_all([prod1, prod2, job])
    db_session.commit()

    text = "Great build quality and sharp OLED panel."
    rev1 = RawReviewIn(product_name="Phone A", raw_review_text=text)
    rev2 = RawReviewIn(product_name="Phone B", raw_review_text=text)

    ins1, dups1 = ingest_review_batch(db_session, [rev1], job, default_product_id=prod1.id)
    ins2, dups2 = ingest_review_batch(db_session, [rev2], job, default_product_id=prod2.id)

    assert ins1 == 1 and dups1 == 0
    assert ins2 == 1 and dups2 == 0
    assert db_session.query(Review).count() == 2
