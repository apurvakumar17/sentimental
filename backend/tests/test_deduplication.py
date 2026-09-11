from backend.app.models.product import Product
from backend.app.models.scraping_job import ScrapingJob
from backend.app.models.review import Review
from backend.app.schemas.review import RawReviewIn
from backend.app.services.ingestion import compute_content_hash, ingest_review_batch

def test_content_hash_consistency():
    hash1 = compute_content_hash(1, "Great phone with clear screen.")
    hash2 = compute_content_hash(1, "   Great   phone with clear screen.  ")
    hash3 = compute_content_hash(2, "Great phone with clear screen.")

    assert hash1 == hash2, "Whitespace normalization must produce identical hashes"
    assert hash1 != hash3, "Different product IDs must produce distinct hashes"

def test_duplicate_review_skipping(db_session):
    product = Product(name="Galaxy S24", brand="Samsung")
    db_session.add(product)
    job = ScrapingJob(target_url="demo://s24", scraper_type="demo", status="RUNNING")
    db_session.add(job)
    db_session.commit()

    reviews = [
        RawReviewIn(
            product_name="Galaxy S24",
            raw_review_text="The battery lasts easily two days.",
            rating=5.0
        ),
        RawReviewIn(
            product_name="Galaxy S24",
            raw_review_text="The battery lasts easily two days.",  # Exact duplicate
            rating=5.0
        ),
        RawReviewIn(
            product_name="Galaxy S24",
            raw_review_text="Speakers are loud and punchy.",     # Unique
            rating=4.5
        )
    ]

    inserted, duplicates = ingest_review_batch(db_session, reviews, job, default_product_id=product.id)

    assert inserted == 2
    assert duplicates == 1

    stored = db_session.query(Review).all()
    assert len(stored) == 2
