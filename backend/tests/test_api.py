from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.scraping_job import ScrapingJob
from backend.app.services.ingestion import compute_content_hash

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "ok"

def test_products_endpoint(client, db_session):
    prod = Product(name="Pixel 8 Pro", brand="Google")
    db_session.add(prod)
    db_session.commit()

    response = client.get("/api/v1/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 1
    assert products[0]["name"] == "Pixel 8 Pro"
    assert products[0]["brand"] == "Google"

def test_reviews_endpoint_filtering(client, db_session):
    prod = Product(name="iPhone 15 Pro", brand="Apple")
    db_session.add(prod)
    db_session.commit()

    rev1 = Review(
        product_id=prod.id,
        review_title="Camera Review",
        raw_review_text="Fantastic low light images.",
        rating=4.8,
        source="demo_catalog",
        content_hash=compute_content_hash(prod.id, "Fantastic low light images.")
    )
    rev2 = Review(
        product_id=prod.id,
        review_title="Battery Issue",
        raw_review_text="Battery drain on 5G network.",
        rating=2.5,
        source="demo_catalog",
        content_hash=compute_content_hash(prod.id, "Battery drain on 5G network.")
    )
    db_session.add_all([rev1, rev2])
    db_session.commit()

    # Query all
    res = client.get("/api/v1/reviews")
    assert res.status_code == 200
    assert res.json()["total"] == 2

    # Query rating filter
    res_high = client.get("/api/v1/reviews?min_rating=4.0")
    assert res_high.status_code == 200
    assert res_high.json()["total"] == 1
    assert res_high.json()["items"][0]["rating"] == 4.8

    # Query search keyword
    res_search = client.get("/api/v1/reviews?q=battery")
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["review_title"] == "Battery Issue"

def test_trigger_scraping_job_api(client):
    payload = {
        "target_url": "demo://iphone-15-pro",
        "scraper_type": "demo",
        "product_name": "Apple iPhone 15 Pro",
        "brand": "Apple",
        "max_pages": 1,
        "delay_seconds": 0.0
    }
    res = client.post("/api/v1/jobs/scrape", json=payload)
    assert res.status_code == 202
    job_data = res.json()
    assert "job_id" in job_data
    assert job_data["status"] == "PENDING"

def test_full_job_execution(db_session):
    import uuid
    from backend.app.services.job_runner import execute_scraping_job

    job_id = str(uuid.uuid4())
    job = ScrapingJob(
        job_id=job_id,
        target_url="demo://galaxy-s24-ultra",
        scraper_type="demo",
        status="PENDING"
    )
    db_session.add(job)
    db_session.commit()

    # Run the worker directly
    execute_scraping_job(
        job_uuid=job_id,
        target_url="demo://galaxy-s24-ultra",
        scraper_type="demo",
        product_name="Samsung Galaxy S24 Ultra",
        brand="Samsung",
        max_pages=2,
        delay_seconds=0.0,
        db_session=db_session
    )

    # Verify job record updated in database
    updated_job = db_session.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    assert updated_job is not None
    assert updated_job.status == "COMPLETED"
    assert updated_job.pages_attempted == 2
    assert updated_job.successful_pages == 2
    assert updated_job.inserted_reviews > 0
