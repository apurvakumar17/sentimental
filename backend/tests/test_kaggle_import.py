import io
import csv
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.scraping_job import ScrapingJob
from backend.app.models.import_job import ImportJob
from backend.app.models.review_import_metadata import ReviewImportMetadata
from backend.app.schemas.import_job import ImportJobResponse
from backend.app.services.kaggle_csv_validator import (
    KAGGLE_REQUIRED_COLUMNS,
    validate_and_preview_csv,
    validate_kaggle_row,
    parse_boolean_value,
    parse_float_value,
)
from backend.app.services.kaggle_importer import execute_kaggle_import_job
from backend.app.scrapers.gsmarena_scraper import (
    GSMArenaReviewScraper,
    CloudflareChallengeError,
    is_cloudflare_challenge,
)
from backend.app.services.job_runner import execute_scraping_job
from backend.app.core.config import settings


# ==============================================================================
# 1. CSV Schema & Row Validation Tests
# ==============================================================================

def test_kaggle_row_validation_valid_row():
    row = {
        "review_id": "1001",
        "customer_name": "Tech Enthusiast",
        "age": "29",
        "brand": "Samsung",
        "model": "Galaxy S24 Ultra",
        "price_usd": "1199.99",
        "price_local": "$1199.99",
        "currency": "USD",
        "exchange_rate_to_usd": "1.0",
        "rating": "4.5",
        "review_text": "Incredible display clarity, fast Snapdragon chipset, and all-day battery.",
        "sentiment": "Positive",
        "country": "United States",
        "language": "English",
        "review_date": "2024-03-15",
        "verified_purchase": "True",
        "battery_life_rating": "5",
        "camera_rating": "5",
        "performance_rating": "5",
        "design_rating": "4",
        "display_rating": "5",
        "review_length": "78",
        "word_count": "10",
        "helpful_votes": "12",
        "source": "Amazon",
    }
    status, issues, clean_data = validate_kaggle_row(row, 1)
    assert status == "valid"
    assert len(issues) == 0
    assert clean_data["external_review_id"] == "1001"
    assert clean_data["customer_name"] == "Tech Enthusiast"
    assert clean_data["verified_purchase"] is True
    assert clean_data["price_usd"] == 1199.99
    assert clean_data["dataset_sentiment"] == "Positive"
    assert clean_data["source"] == "Amazon"


def test_kaggle_row_validation_blank_text_rejected():
    row = {
        "review_id": "1002",
        "customer_name": "User2",
        "brand": "Google",
        "model": "Pixel 9",
        "rating": "4.0",
        "review_text": "   ",  # Blank review text
        "source": "BestBuy",
    }
    status, issues, clean_data = validate_kaggle_row(row, 2)
    assert status == "rejected"
    assert any("blank or missing" in iss for iss in issues)


def test_kaggle_row_validation_missing_identifiers_rejected():
    # Missing review_id
    row_no_id = {
        "review_id": "",
        "brand": "Apple",
        "model": "iPhone 15",
        "review_text": "Good phone.",
    }
    status1, issues1, _ = validate_kaggle_row(row_no_id, 3)
    assert status1 == "rejected"
    assert any("review_id" in iss for iss in issues1)

    # Missing brand and model
    row_no_model = {
        "review_id": "1003",
        "brand": "",
        "model": "",
        "review_text": "Great screen quality.",
    }
    status2, issues2, _ = validate_kaggle_row(row_no_model, 4)
    assert status2 == "rejected"
    assert any("Both 'model' and 'brand' are missing" in iss for iss in issues2)


def test_kaggle_row_validation_warnings_on_edge_values():
    row = {
        "review_id": "1004",
        "brand": "OnePlus",
        "model": "OnePlus 12",
        "rating": "5.0",
        "review_text": "Ok.",  # Very short (<10 chars)
        "sentiment": "UnknownSentiment",  # Non-standard sentiment
        "review_date": "invalid-date-string",  # Unparseable date
        "battery_life_rating": "9.0",  # Out of [1.0, 5.0] bounds
    }
    status, issues, clean_data = validate_kaggle_row(row, 5)
    assert status == "warning"
    assert any("short" in iss for iss in issues)
    assert any("sentiment" in iss for iss in issues)
    assert any("review_date" in iss for iss in issues)
    assert any("battery_life_rating" in iss for iss in issues)
    assert clean_data["review_date"] is None
    assert clean_data["review_date_raw"] == "invalid-date-string"


def test_boolean_and_numerical_parsers():
    assert parse_boolean_value("True") is True
    assert parse_boolean_value("1") is True
    assert parse_boolean_value("yes") is True
    assert parse_boolean_value("False") is False
    assert parse_boolean_value("0") is False
    assert parse_boolean_value(None) is None
    assert parse_boolean_value("") is None

    assert parse_float_value("4.75") == 4.75
    assert parse_float_value("  3.0 ") == 3.0
    assert parse_float_value("not_a_number") is None
    assert parse_float_value("") is None


# ==============================================================================
# 2. CSV File Preview & Validation Service Tests
# ==============================================================================

def test_validate_and_preview_csv_exact_schema(tmp_path):
    csv_file = tmp_path / "valid_sample.csv"
    headers = KAGGLE_REQUIRED_COLUMNS
    rows = [
        ["1", "Alice", "30", "Apple", "iPhone 16", "999.0", "$999", "USD", "1.0", "5.0", "Fast A18 processor with solid battery life.", "Positive", "US", "en", "2024-09-20", "True", "5", "5", "5", "5", "5", "46", "7", "4", "BestBuy"],
        ["2", "Bob", "40", "Google", "Pixel 9 Pro", "899.0", "$899", "USD", "1.0", "4.0", "Super clean software experience.", "Positive", "US", "en", "2024-09-21", "True", "4", "5", "4", "4", "5", "33", "4", "1", "Amazon"],
    ]
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    res = validate_and_preview_csv(csv_file)
    assert res["is_schema_valid"] is True
    assert len(res["missing_columns"]) == 0
    assert res["total_rows_scanned"] == 2
    assert res["valid_row_count"] == 2
    assert res["rejected_row_count"] == 0
    assert len(res["sample_rows"]) == 2
    assert res["sample_rows"][0]["model"] == "iPhone 16"


def test_validate_and_preview_csv_missing_columns(tmp_path):
    csv_file = tmp_path / "missing_cols.csv"
    incomplete_headers = ["review_id", "customer_name", "rating", "review_text"]
    with open(csv_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(incomplete_headers)
        writer.writerow(["1", "Sam", "5.0", "Great product!"])

    res = validate_and_preview_csv(csv_file)
    assert res["is_schema_valid"] is False
    assert "model" in res["missing_columns"]
    assert "brand" in res["missing_columns"]
    assert "source" in res["missing_columns"]


def test_validate_and_preview_does_not_modify_database(db_session, tmp_path):
    initial_reviews = db_session.query(Review).count()
    initial_products = db_session.query(Product).count()

    csv_file = tmp_path / "preview_only.csv"
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(KAGGLE_REQUIRED_COLUMNS)
        writer.writerow(["99", "Tester", "25", "Motorola", "Edge 50", "499", "$499", "USD", "1.0", "4.0", "Great display and slim chassis.", "Positive", "US", "en", "2024-05-01", "True", "4", "4", "4", "5", "4", "32", "5", "0", "Amazon"])

    res = validate_and_preview_csv(csv_file)
    assert res["is_schema_valid"] is True

    # Database state must be completely untouched
    assert db_session.query(Review).count() == initial_reviews
    assert db_session.query(Product).count() == initial_products


# ==============================================================================
# 3. Batch Importer & Deduplication Tests
# ==============================================================================

def test_kaggle_batch_import_successful(db_session, tmp_path):
    csv_file = tmp_path / "import_test.csv"
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(KAGGLE_REQUIRED_COLUMNS)
        # Row 1: Apple iPhone 15
        writer.writerow(["K101", "User A", "28", "Apple", "iPhone 15", "799.0", "$799", "USD", "1.0", "4.5", "Great Dynamic Island screen and smooth USB-C transition.", "Positive", "USA", "English", "2024-01-10", "True", "4", "5", "5", "5", "5", "58", "8", "5", "BestBuy"])
        # Row 2: Same product (Apple iPhone 15), different review
        writer.writerow(["K102", "User B", "35", "Apple", "iPhone 15", "799.0", "$799", "USD", "1.0", "3.0", "Battery life is mediocre for heavy gaming.", "Neutral", "USA", "English", "2024-01-12", "True", "2", "4", "4", "4", "4", "41", "7", "2", "BestBuy"])
        # Row 3: Different product (Samsung Galaxy S24)
        writer.writerow(["K103", "User C", "42", "Samsung", "Galaxy S24", "799.0", "$799", "USD", "1.0", "4.0", "Compact size with great flat AMOLED display.", "Positive", "USA", "English", "2024-01-15", "False", "4", "4", "4", "4", "5", "43", "7", "0", "Amazon"])

    job = ImportJob(
        job_id="test-job-uuid-001",
        original_filename="import_test.csv",
        server_filepath=str(csv_file),
        status="PENDING",
    )
    db_session.add(job)
    db_session.commit()

    execute_kaggle_import_job(
        job_uuid="test-job-uuid-001",
        file_path=csv_file,
        batch_size=2,
        db_session=db_session,
    )

    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.rows_processed == 3
    assert job.rows_inserted == 3
    assert job.duplicate_rows_skipped == 0
    assert job.rejected_rows == 0

    # Verify Product Reuse: Exactly 2 distinct products created, not 3
    prods = db_session.query(Product).all()
    assert len(prods) == 2
    iphone = db_session.query(Product).filter(Product.name == "iPhone 15").first()
    assert iphone is not None
    assert len(iphone.reviews) == 2

    # Verify Review & Metadata persistence
    r1 = db_session.query(Review).filter(Review.external_review_id == "K101").first()
    assert r1 is not None
    assert r1.ingestion_method == "kaggle_import"
    assert r1.source == "BestBuy"
    assert r1.import_metadata is not None
    assert r1.import_metadata.age == 28
    assert r1.import_metadata.dataset_sentiment == "Positive"
    assert r1.import_metadata.battery_life_rating == 4.0
    assert r1.import_metadata.price_usd == 799.0


def test_kaggle_batch_import_deduplication(db_session, tmp_path):
    csv_file = tmp_path / "dedup_test.csv"
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(KAGGLE_REQUIRED_COLUMNS)
        # Original
        writer.writerow(["DUP1", "Alice", "30", "Xiaomi", "14 Ultra", "999", "$999", "USD", "1.0", "5.0", "Superb Leica camera lenses.", "Positive", "US", "en", "2024-02-01", "True", "5", "5", "5", "5", "5", "27", "4", "1", "AliExpress"])
        # Exact duplicate in same file (same review_id & same source)
        writer.writerow(["DUP1", "Alice", "30", "Xiaomi", "14 Ultra", "999", "$999", "USD", "1.0", "5.0", "Superb Leica camera lenses.", "Positive", "US", "en", "2024-02-01", "True", "5", "5", "5", "5", "5", "27", "4", "1", "AliExpress"])
        # Second duplicate text with different external id
        writer.writerow(["DUP2", "Bob", "31", "Xiaomi", "14 Ultra", "999", "$999", "USD", "1.0", "5.0", "Superb Leica camera lenses.", "Positive", "US", "en", "2024-02-01", "True", "5", "5", "5", "5", "5", "27", "4", "1", "AliExpress"])

    job1 = ImportJob(
        job_id="test-job-uuid-dedup-1",
        original_filename="dedup_test.csv",
        status="PENDING",
    )
    db_session.add(job1)
    db_session.commit()

    execute_kaggle_import_job(
        job_uuid="test-job-uuid-dedup-1",
        file_path=csv_file,
        batch_size=10,
        db_session=db_session,
    )

    db_session.refresh(job1)
    assert job1.status == "COMPLETED"
    assert job1.rows_inserted == 1
    assert job1.duplicate_rows_skipped == 2

    # Re-importing the same file must skip ALL records as duplicates
    job2 = ImportJob(
        job_id="test-job-uuid-dedup-2",
        original_filename="dedup_test.csv",
        status="PENDING",
    )
    db_session.add(job2)
    db_session.commit()

    execute_kaggle_import_job(
        job_uuid="test-job-uuid-dedup-2",
        file_path=csv_file,
        batch_size=10,
        db_session=db_session,
    )

    db_session.refresh(job2)
    assert job2.status == "COMPLETED"
    assert job2.rows_inserted == 0
    assert job2.duplicate_rows_skipped == 3


def test_kaggle_import_preserves_distinct_products_and_sources(db_session, tmp_path):
    csv_file = tmp_path / "distinct_test.csv"
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(KAGGLE_REQUIRED_COLUMNS)
        # Identical text for Phone A
        writer.writerow(["ID_A", "User", "20", "BrandA", "Phone A", "200", "$200", "USD", "1.0", "4.0", "Good value for money.", "Positive", "US", "en", "2024-01-01", "True", "4", "4", "4", "4", "4", "21", "4", "0", "Amazon"])
        # Identical text for Phone B (Must NOT merge or collide!)
        writer.writerow(["ID_B", "User", "20", "BrandB", "Phone B", "300", "$300", "USD", "1.0", "4.0", "Good value for money.", "Positive", "US", "en", "2024-01-01", "True", "4", "4", "4", "4", "4", "21", "4", "0", "Amazon"])

    job = ImportJob(job_id="test-job-distinct", original_filename="distinct_test.csv", status="PENDING")
    db_session.add(job)
    db_session.commit()

    execute_kaggle_import_job(job_uuid="test-job-distinct", file_path=csv_file, db_session=db_session)
    db_session.refresh(job)
    assert job.rows_inserted == 2
    assert job.duplicate_rows_skipped == 0


# ==============================================================================
# 4. API Endpoints Integration Tests
# ==============================================================================

def test_api_import_preview_endpoint(client, tmp_path):
    csv_content = (
        ",".join(KAGGLE_REQUIRED_COLUMNS) + "\n"
        "P1,Cust,30,Apple,iPhone 16,999,$999,USD,1.0,5.0,Fast performance.,Positive,US,en,2024-09-20,True,5,5,5,5,5,17,2,0,Amazon\n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/v1/imports/preview", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["is_schema_valid"] is True
    assert data["total_rows_scanned"] == 1
    assert data["valid_row_count"] == 1
    assert len(data["sample_rows"]) == 1


def test_api_import_preview_rejects_non_csv(client):
    files = {"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")}
    res = client.post("/api/v1/imports/preview", files=files)
    assert res.status_code == 400
    assert "Only CSV files" in res.json()["detail"]


def test_api_import_job_lifecycle_and_errors(client, db_session):
    csv_content = (
        ",".join(KAGGLE_REQUIRED_COLUMNS) + "\n"
        "E1,User1,25,Realme,GT 6,400,$400,USD,1.0,4.0,Solid AMOLED display.,Positive,IN,en,2024-07-01,True,4,4,4,4,4,21,3,0,Flipkart\n"
        "E2,User2,26,Realme,GT 6,400,$400,USD,1.0,4.0,,Positive,IN,en,2024-07-01,True,4,4,4,4,4,0,0,0,Flipkart\n"  # blank review text
    )
    files = {"file": ("sample_upload.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

    # 1. Start import job
    post_res = client.post("/api/v1/imports", files=files)
    assert post_res.status_code == 201
    job_data = post_res.json()
    job_id = job_data["job_id"]
    assert job_data["original_filename"] == "sample_upload.csv"

    # 2. Get import status
    status_res = client.get(f"/api/v1/imports/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["job_id"] == job_id

    # 3. List import jobs
    list_res = client.get("/api/v1/imports")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1


def test_imported_reviews_appear_in_warehouse_and_quality(client, db_session, tmp_path):
    csv_file = tmp_path / "warehouse_test.csv"
    with open(csv_file, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(KAGGLE_REQUIRED_COLUMNS)
        writer.writerow(["WH1", "ReviewerX", "33", "Google", "Pixel 8a", "499", "$499", "USD", "1.0", "4.8", "Vibrant 120Hz display with outstanding camera quality.", "Positive", "US", "en", "2024-05-14", "True", "4", "5", "4", "4", "5", "54", "7", "3", "Amazon"])

    job = ImportJob(job_id="test-wh-job", original_filename="warehouse_test.csv", status="PENDING")
    db_session.add(job)
    db_session.commit()

    execute_kaggle_import_job(job_uuid="test-wh-job", file_path=csv_file, db_session=db_session)

    # 1. Appears in /api/v1/reviews
    rev_res = client.get("/api/v1/reviews?source=Amazon")
    assert rev_res.status_code == 200
    items = rev_res.json()["items"]
    assert any(r["external_review_id"] == "WH1" for r in items)

    # 2. Filter by ingestion_method
    method_res = client.get("/api/v1/reviews?ingestion_method=kaggle_import")
    assert method_res.status_code == 200
    assert any(r["external_review_id"] == "WH1" for r in method_res.json()["items"])

    # 3. Evaluated by /api/v1/datasets/quality
    qual_res = client.post("/api/v1/datasets/quality")
    assert qual_res.status_code == 200
    q_data = qual_res.json()
    assert q_data["total_reviews"] >= 1


# ==============================================================================
# 5. Cloudflare Challenge Detection Tests
# ==============================================================================

def test_cloudflare_challenge_detector_function():
    cf_html = "<html><head><title>Just a moment...</title></head><body><div id='cf-turnstile'></div><div class='ray-id'>Ray ID: 1234</div></body></html>"
    assert is_cloudflare_challenge(200, cf_html) is True
    assert is_cloudflare_challenge(403, "<html><body>Forbidden by Cloudflare</body></html>") is True
    assert is_cloudflare_challenge(503, "<html><div id='challenge-running'>Verify you are human</div></html>") is True

    valid_html = "<html><head><title>Samsung Galaxy S24 - User Opinions</title></head><body><div class='user-thread'>Great phone</div></body></html>"
    assert is_cloudflare_challenge(200, valid_html) is False


def test_gsmarena_scraper_raises_cloudflare_challenge_error():
    scraper = GSMArenaReviewScraper()
    # Offline challenge fixture: gsmarena://cloudflare-challenge
    with pytest.raises(CloudflareChallengeError) as exc_info:
        scraper.fetch_page_content("gsmarena://cloudflare-challenge", 1)

    assert "Cloudflare human verification challenge encountered" in str(exc_info.value)
    assert "Dataset Import" in str(exc_info.value)


def test_job_runner_marks_failed_and_advises_kaggle_import_on_challenge(db_session):
    job = ScrapingJob(
        job_id="test-challenge-job-uuid",
        target_url="gsmarena://cloudflare-challenge",
        scraper_type="gsmarena",
        status="PENDING",
    )
    db_session.add(job)
    db_session.commit()

    execute_scraping_job(
        job_uuid="test-challenge-job-uuid",
        target_url="gsmarena://cloudflare-challenge",
        scraper_type="gsmarena",
        db_session=db_session,
    )

    db_session.refresh(job)
    assert job.status == "FAILED"
    assert "Cloudflare human verification challenge" in job.error_log
    assert "Dataset Import" in job.error_log
