import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.scraping_job import ScrapingJob
from backend.app.models.import_job import ImportJob
from backend.app.models.review_import_metadata import ReviewImportMetadata

client = TestClient(app)


def test_clear_database_endpoint(client: TestClient, db_session: Session):
    db = db_session
    # 1. Populate test data
    prod = Product(name="Test Phone Clear", brand="ClearBrand")
    db.add(prod)
    db.commit()

    job = ScrapingJob(job_id="test-clear-job", target_url="http://test.com", status="COMPLETED")
    db.add(job)
    db.commit()

    import_job = ImportJob(job_id="test-clear-import", original_filename="test.csv", status="COMPLETED")
    db.add(import_job)
    db.commit()

    rev = Review(
        product_id=prod.id,
        scraping_job_id=job.id,
        raw_review_text="Test review text to clear",
        rating=4.5,
        source="TestClear",
        content_hash="clearhash123",
        ingestion_method="scraper"
    )
    db.add(rev)
    db.commit()

    meta = ReviewImportMetadata(
        review_id=rev.id,
        age=25,
        dataset_sentiment="positive"
    )
    db.add(meta)
    db.commit()

    # Verify counts before clearing
    assert db.query(Product).count() >= 1
    assert db.query(Review).count() >= 1
    assert db.query(ScrapingJob).count() >= 1
    assert db.query(ImportJob).count() >= 1
    assert db.query(ReviewImportMetadata).count() >= 1

    # 2. Call clear database endpoint
    res = client.post("/api/v1/system/clear-database")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "deleted" in data
    assert data["deleted"]["reviews"] >= 1
    assert data["deleted"]["products"] >= 1

    # 3. Verify counts after clearing
    assert db.query(ReviewImportMetadata).count() == 0
    assert db.query(Review).count() == 0
    assert db.query(Product).count() == 0
    assert db.query(ScrapingJob).count() == 0
    assert db.query(ImportJob).count() == 0

    # 4. Calling again on empty database succeeds
    res2 = client.post("/api/v1/system/clear-database")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["deleted"]["reviews"] == 0
    assert data2["deleted"]["products"] == 0
