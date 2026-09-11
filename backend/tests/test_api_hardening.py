def test_api_rejects_unregistered_scraper(client):
    payload = {
        "target_url": "demo://iphone-15",
        "scraper_type": "completely_bogus_adapter",
        "max_pages": 1
    }
    response = client.post("/api/v1/jobs/scrape", json=payload)
    assert response.status_code == 400
    assert "Unsupported scraper type" in response.json()["detail"]

def test_api_rejects_invalid_url_scheme(client):
    payload = {
        "target_url": "ftp://invalidscheme.com/reviews",
        "scraper_type": "demo",
        "max_pages": 1
    }
    response = client.post("/api/v1/jobs/scrape", json=payload)
    assert response.status_code == 422

def test_api_missing_resource_returns_404(client):
    res1 = client.get("/api/v1/products/999999")
    assert res1.status_code == 404
    assert res1.json()["detail"] == "Product not found"

    res2 = client.get("/api/v1/reviews/999999")
    assert res2.status_code == 404
    assert res2.json()["detail"] == "Review not found"

def test_api_job_with_max_reviews(client):
    payload = {
        "target_url": "demo://iphone-15-pro",
        "scraper_type": "demo",
        "product_name": "Apple iPhone 15 Pro",
        "max_pages": 2,
        "max_reviews": 5,
        "delay_seconds": 0.0
    }
    response = client.post("/api/v1/jobs/scrape", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["max_reviews"] == 5

def test_api_accepts_gsmarena_scraper(client):
    payload = {
        "target_url": "https://www.gsmarena.com/apple_iphone_15_pro-reviews-12557.php",
        "scraper_type": "gsmarena",
        "product_name": "Apple iPhone 15 Pro",
        "brand": "Apple",
        "max_pages": 1,
        "delay_seconds": 0.0
    }
    response = client.post("/api/v1/jobs/scrape", json=payload)
    assert response.status_code == 202
    assert response.json()["scraper_type"] == "gsmarena"

def test_complete_deterministic_pipeline(client, db_session):
    """
    End-to-End Deterministic Integration:
    Create Product -> Trigger Scrape -> Execute -> Ingest & Deduplicate -> Query Reviews & Stats
    """
    # 1. Create Product
    prod_res = client.post("/api/v1/products", json={"name": "OnePlus 12", "brand": "OnePlus"})
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]

    # 2. Trigger Scrape
    job_res = client.post("/api/v1/jobs/scrape", json={
        "target_url": "demo://oneplus-12",
        "scraper_type": "demo",
        "product_name": "OnePlus 12",
        "brand": "OnePlus",
        "max_pages": 1,
        "delay_seconds": 0.0
    })
    assert job_res.status_code == 202
    job_uuid = job_res.json()["job_id"]

    # 3. Execute Worker
    from backend.app.services.job_runner import execute_scraping_job
    execute_scraping_job(
        job_uuid=job_uuid,
        target_url="demo://oneplus-12",
        scraper_type="demo",
        product_name="OnePlus 12",
        brand="OnePlus",
        max_pages=1,
        delay_seconds=0.0,
        db_session=db_session
    )

    # 4. Verify Job completion via API
    job_status_res = client.get(f"/api/v1/jobs/{job_uuid}")
    assert job_status_res.status_code == 200
    assert job_status_res.json()["status"] == "COMPLETED"

    # 5. Query reviews for this product
    reviews_res = client.get(f"/api/v1/reviews?product_id={prod_id}")
    assert reviews_res.status_code == 200
    assert reviews_res.json()["total"] > 0
