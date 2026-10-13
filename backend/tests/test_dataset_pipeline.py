import io
import csv
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.core.normalization import safe_normalize_text, get_text_stats
from backend.app.schemas.dataset import DataQualityConfig, DatasetFilterOptions, DatasetExportRequest
from backend.app.services.data_quality import evaluate_dataset_quality, assess_review_record
from backend.app.services.dataset_export import (
    prepare_review_dataset,
    export_dataset_to_file,
    list_dataset_manifests,
    get_safe_export_path,
)
from backend.app.services.dataset_splitting import split_prepared_dataset


# ==============================================================================
# 1. Preprocessing & Safe Normalization Tests
# ==============================================================================

def test_safe_preprocessing_preserves_sentiment_tokens():
    raw = "The camera is NOT bad at all! But battery life is 100% terrible... 📱✨"
    normalized = safe_normalize_text(raw)
    assert "NOT" in normalized
    assert "!" in normalized
    assert "100%" in normalized
    assert "📱✨" in normalized
    assert "terrible" in normalized


def test_safe_preprocessing_html_entities_and_whitespace():
    raw = "Screen is sharp &amp; bright.<br>Colors are &quot;vivid&quot;.\n\n\nReally fast."
    normalized = safe_normalize_text(raw)
    assert "&amp;" not in normalized
    assert "&" in normalized
    assert '"vivid"' in normalized
    assert "<br>" not in normalized
    assert "\n\n" not in normalized
    assert normalized == 'Screen is sharp & bright. Colors are "vivid". Really fast.'


def test_safe_preprocessing_empty_and_whitespace():
    assert safe_normalize_text("") == ""
    assert safe_normalize_text("   \n\t  ") == ""
    assert safe_normalize_text("<p>   <br/> </p>") == ""


def test_get_text_stats():
    text = "Great smartphone display and camera"
    stats = get_text_stats(text)
    assert stats["char_count"] == len(text)
    assert stats["word_count"] == 5

    empty_stats = get_text_stats("")
    assert empty_stats["char_count"] == 0
    assert empty_stats["word_count"] == 0


# ==============================================================================
# 2. Data Quality Assessment Tests
# ==============================================================================

def test_data_quality_clean_records(db_session):
    prod = Product(name="Google Pixel 9 Pro", brand="Google")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text="Outstanding display brightness and balanced camera zoom processing.",
        normalized_review_text="Outstanding display brightness and balanced camera zoom processing.",
        rating=4.8,
        reviewer_name="TechReviewer",
        review_date=datetime.now(timezone.utc).date(),
        source="demo",
        content_hash="clean_hash_001"
    )
    db_session.add(rev)
    db_session.commit()

    summary = evaluate_dataset_quality(db=db_session, product_id=prod.id)
    assert summary.total_reviews == 1
    assert summary.valid_reviews == 1
    assert summary.clean_reviews == 1
    assert summary.reviews_with_errors == 0
    assert summary.quality_score == 100.0


def test_data_quality_detects_fatal_errors(db_session):
    prod = Product(name="Test Device", brand="TestBrand")
    db_session.add(prod)
    db_session.commit()

    # 1. Missing text review
    rev_blank = Review(
        product_id=prod.id,
        raw_review_text="   ",
        normalized_review_text="",
        source="demo",
        content_hash="blank_hash_001"
    )
    # 2. Normalization-empty review (only HTML tags)
    rev_norm_empty = Review(
        product_id=prod.id,
        raw_review_text="<p><br></p>",
        normalized_review_text="",
        source="demo",
        content_hash="html_empty_hash_002"
    )
    # 3. Invalid rating review (out of bounds)
    rev_invalid_rating = Review(
        product_id=prod.id,
        raw_review_text="Solid build quality.",
        normalized_review_text="Solid build quality.",
        rating=9.5, # invalid
        source="demo",
        content_hash="invalid_rate_hash_003"
    )

    db_session.add_all([rev_blank, rev_norm_empty, rev_invalid_rating])
    db_session.commit()

    summary = evaluate_dataset_quality(db=db_session, product_id=prod.id)
    assert summary.missing_text_count == 1
    assert summary.normalization_empty_count == 1
    assert summary.invalid_rating_count == 1
    assert summary.reviews_with_errors == 3
    assert summary.valid_reviews == 0
    assert summary.quality_score < 50.0


def test_data_quality_duplicate_and_warning_detection(db_session):
    prod = Product(name="Apple iPhone 16", brand="Apple")
    db_session.add(prod)
    db_session.commit()

    # Original
    rev1 = Review(
        product_id=prod.id,
        raw_review_text="Smooth ProMotion screen and great battery life.",
        normalized_review_text="Smooth ProMotion screen and great battery life.",
        source="demo",
        reviewer_name="User1",
        content_hash="dup_hash_shared_1"
    )
    # Potential duplicate (same product & normalized text, different hash)
    rev2 = Review(
        product_id=prod.id,
        raw_review_text="Smooth ProMotion screen and great battery life.",
        normalized_review_text="Smooth ProMotion screen and great battery life.",
        source="demo",
        reviewer_name="User2",
        content_hash="dup_hash_shared_2"
    )
    # Excessively short review (< 10 chars)
    rev3 = Review(
        product_id=prod.id,
        raw_review_text="Nice.",
        normalized_review_text="Nice.",
        source="demo",
        reviewer_name="User3",
        content_hash="short_hash_003"
    )

    db_session.add_all([rev1, rev2, rev3])
    db_session.commit()

    summary = evaluate_dataset_quality(db=db_session, product_id=prod.id)
    assert summary.total_reviews == 3
    assert summary.potential_duplicate_count == 1
    assert summary.excessively_short_count == 1
    # Quality score penalizes duplicates and warnings softly without dropping to zero
    assert 50.0 <= summary.quality_score < 100.0


def test_assess_review_record_exact_duplicate_unit():
    from unittest.mock import MagicMock
    cfg = DataQualityConfig()
    r1 = MagicMock(id=1, product_id=1, raw_review_text="Identical content", normalized_review_text="Identical content", rating=4.0, reviewer_name="A", review_date=None, review_date_raw="2026", source="test", content_hash="same_exact_hash")
    r2 = MagicMock(id=2, product_id=1, raw_review_text="Identical content", normalized_review_text="Identical content", rating=4.0, reviewer_name="B", review_date=None, review_date_raw="2026", source="test", content_hash="same_exact_hash")

    seen_hashes = {}
    seen_text = {}
    issues1, _ = assess_review_record(r1, cfg, seen_hashes, seen_text)
    issues2, _ = assess_review_record(r2, cfg, seen_hashes, seen_text)
    assert not any(i.issue_type == "exact_duplicate" for i in issues1)
    assert any(i.issue_type == "exact_duplicate" for i in issues2)


# ==============================================================================
# 3. Dataset Preparation & Filtering Tests
# ==============================================================================

def test_prepare_dataset_deterministic_filtering(db_session):
    prod1 = Product(name="Phone Alpha", brand="AlphaBrand")
    prod2 = Product(name="Phone Beta", brand="BetaBrand")
    db_session.add_all([prod1, prod2])
    db_session.commit()

    r1 = Review(product_id=prod1.id, raw_review_text="Alpha review one", source="gsmarena", rating=4.0, content_hash="h1")
    r2 = Review(product_id=prod1.id, raw_review_text="Alpha review two", source="gsmarena", rating=4.5, content_hash="h2")
    r3 = Review(product_id=prod2.id, raw_review_text="Beta review one", source="demo", rating=3.0, content_hash="h3")
    r_bad = Review(product_id=prod1.id, raw_review_text="   ", source="gsmarena", rating=5.0, content_hash="h_bad")

    db_session.add_all([r1, r2, r3, r_bad])
    db_session.commit()

    # 1. Filter by product1 with exclude_errors=True
    filters1 = DatasetFilterOptions(product_id=prod1.id, exclude_errors=True)
    records1, total_examined, exclusions = prepare_review_dataset(db_session, filters=filters1)
    assert total_examined == 3 # r1, r2, r_bad
    assert len(records1) == 2 # r_bad excluded due to blank text error
    assert exclusions["errors"] == 1
    assert [rec.review_id for rec in records1] == [r1.id, r2.id] # Deterministic ordering by ID

    # 2. Filter by min_rating >= 4.0
    filters_rating = DatasetFilterOptions(min_rating=4.0, exclude_errors=True)
    records_rating, _, _ = prepare_review_dataset(db_session, filters=filters_rating)
    assert len(records_rating) == 2
    assert all(rec.rating >= 4.0 for rec in records_rating)


# ==============================================================================
# 4. Dataset Export Tests (CSV & JSONL)
# ==============================================================================

def test_dataset_export_csv_and_manifest(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", tmp_path)

    prod = Product(name="Galaxy S25 Ultra", brand="Samsung")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text='Camera has 5x "optical" zoom, and battery is 5000mAh.',
        source="gsmarena",
        rating=4.7,
        reviewer_name="GamerGuy",
        content_hash="csv_test_hash"
    )
    db_session.add(rev)
    db_session.commit()

    manifest = export_dataset_to_file(db_session, export_format="csv")
    assert manifest.format == "csv"
    assert manifest.total_exported_records == 1
    assert manifest.sha256_checksum is not None

    export_file = tmp_path / manifest.filename
    assert export_file.exists()
    assert export_file.stat().st_size > 0

    # Read and verify CSV format
    with open(export_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        row = rows[0]
        assert row["product_name"] == "Galaxy S25 Ultra"
        assert row["annotation_status"] == "UNANNOTATED"
        assert '5x "optical" zoom' in row["raw_review_text"]


def test_dataset_export_jsonl(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", tmp_path)

    prod = Product(name="OnePlus 12", brand="OnePlus")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text="Fast 100W SuperVOOC charging is incredible.",
        source="demo",
        rating=4.6,
        content_hash="jsonl_test_hash"
    )
    db_session.add(rev)
    db_session.commit()

    manifest = export_dataset_to_file(db_session, export_format="jsonl")
    assert manifest.format == "jsonl"
    export_file = tmp_path / manifest.filename

    with open(export_file, mode="r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        item = json.loads(lines[0])
        assert item["product_name"] == "OnePlus 12"
        assert item["annotation_status"] == "UNANNOTATED"


def test_safe_export_path_traversal_rejection(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", tmp_path)

    # Valid file creation
    valid_file = tmp_path / "valid.csv"
    valid_file.write_text("a,b,c")

    assert get_safe_export_path("valid.csv") == valid_file

    # Directory traversal attempts must raise ValueError
    with pytest.raises(ValueError):
        get_safe_export_path("../../../etc/passwd")

    with pytest.raises(ValueError):
        get_safe_export_path("sub/folder/file.csv")

    with pytest.raises(FileNotFoundError):
        get_safe_export_path("non_existent_file.csv")


# ==============================================================================
# 5. Dataset Splitting Tests
# ==============================================================================

def test_dataset_splitting_reproducibility_and_no_leakage():
    records = [
        {"review_id": i, "product_id": 1, "normalized_review_text": f"Unique review {i}"}
        for i in range(100)
    ]
    # Add an exact duplicate text to verify it stays in the same split
    records.append({"review_id": 101, "product_id": 1, "normalized_review_text": "Unique review 5"})

    res1 = split_prepared_dataset(records, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, random_seed=42)
    res2 = split_prepared_dataset(records, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, random_seed=42)

    assert res1["split_counts"]["train"] == res2["split_counts"]["train"]
    assert res1["split_counts"]["val"] == res2["split_counts"]["val"]
    assert res1["split_counts"]["test"] == res2["split_counts"]["test"]

    # Check duplicate clustering: review 5 and review 101 must be in the same split!
    split_5 = next(r["split"] for r in res1["train"] + res1["val"] + res1["test"] if r["review_id"] == 5)
    split_101 = next(r["split"] for r in res1["train"] + res1["val"] + res1["test"] if r["review_id"] == 101)
    assert split_5 == split_101


# ==============================================================================
# 6. API Integration Tests
# ==============================================================================

def test_api_dataset_quality_endpoint(client, db_session):
    prod = Product(name="API Test Phone", brand="TestBrand")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text="Excellent haptics and stereo sound quality.",
        source="demo",
        reviewer_name="AudioFan",
        rating=4.5,
        content_hash="api_quality_hash"
    )
    db_session.add(rev)
    db_session.commit()

    res = client.post(f"/api/v1/datasets/quality?product_id={prod.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["total_reviews"] == 1
    assert data["valid_reviews"] == 1
    assert data["quality_score"] == 100.0


def test_api_dataset_preview_endpoint(client, db_session):
    prod = Product(name="Preview Phone", brand="BrandX")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text="Great AMOLED screen with 120Hz refresh rate.",
        source="demo",
        content_hash="api_prev_hash"
    )
    db_session.add(rev)
    db_session.commit()

    res = client.post("/api/v1/datasets/preview?limit=5", json={"product_id": prod.id})
    assert res.status_code == 200
    data = res.json()
    assert data["preview_count"] == 1
    record = data["records"][0]
    assert record["product_name"] == "Preview Phone"
    assert record["annotation_status"] == "UNANNOTATED"


def test_api_dataset_export_and_download_flow(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EXPORTS_DIR", tmp_path)

    prod = Product(name="Export Phone", brand="BrandY")
    db_session.add(prod)
    db_session.commit()

    rev = Review(
        product_id=prod.id,
        raw_review_text="Stunning design with slim bezels.",
        source="demo",
        content_hash="api_exp_hash"
    )
    db_session.add(rev)
    db_session.commit()

    # 1. Trigger export
    exp_res = client.post("/api/v1/datasets/export", json={"format": "csv"})
    assert exp_res.status_code == 201
    manifest = exp_res.json()
    filename = manifest["filename"]
    assert filename.endswith(".csv")

    # 2. List exports
    list_res = client.get("/api/v1/datasets/exports")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Download export file
    dl_res = client.get(f"/api/v1/datasets/download/{filename}")
    assert dl_res.status_code == 200
    assert "Stunning design with slim bezels" in dl_res.text

    # 4. Path traversal attempt must return 400
    bad_res = client.get("/api/v1/datasets/download/..%2F..%2Fetc%2Fpasswd")
    assert bad_res.status_code in (400, 404)
