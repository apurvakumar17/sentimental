import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.import_job import ImportJob
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.review_import_metadata import ReviewImportMetadata
from backend.app.core.normalization import safe_normalize_text
from backend.app.services.ingestion import compute_content_hash
from backend.app.services.kaggle_csv_validator import (
    KAGGLE_REQUIRED_COLUMNS,
    validate_kaggle_row,
)

logger = logging.getLogger("smartreview.kaggle_importer")


def execute_kaggle_import_job(
    job_uuid: str,
    file_path: Path,
    batch_size: int = 500,
    db_session: Optional[Session] = None,
    cleanup_temp_file: bool = False,
):
    """
    Executes a high-volume Kaggle CSV dataset import in bounded batches.
    Guarantees:
      - Periodic transaction commits (every batch_size rows).
      - Product reuse across rows.
      - 3-tier deduplication (skips duplicates without failing).
      - Incremental progress tracking on ImportJob.
      - Proper database session cleanup.
      - FAILED status transition on unexpected errors.
    """
    close_db_when_done = False
    if db_session is not None:
        db = db_session
    else:
        db = SessionLocal()
        close_db_when_done = True

    try:
        job = db.query(ImportJob).filter(ImportJob.job_id == job_uuid).first()
        if not job:
            logger.error(f"ImportJob {job_uuid} not found in database.")
            return

        job.status = "PROCESSING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        if not file_path.exists():
            job.status = "FAILED"
            job.error_summary = f"Uploaded file not found on disk at {file_path.name}"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return

        # Read CSV headers
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f)
            try:
                raw_headers = next(reader)
            except StopIteration:
                job.status = "FAILED"
                job.error_summary = "CSV file is empty."
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
                return

            detected_cols = [h.strip().lower() for h in raw_headers]
            required_set = set(KAGGLE_REQUIRED_COLUMNS)
            missing = [c for c in KAGGLE_REQUIRED_COLUMNS if c not in set(detected_cols)]
            if missing:
                job.status = "FAILED"
                job.error_summary = f"Missing required CSV columns: {', '.join(missing)}"
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
                return

            # Estimate or calculate total rows
            row_count_estimate = sum(1 for _ in reader)
            job.total_rows = row_count_estimate
            db.commit()

        # Reopen file for data processing
        with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header

            # 1. Product Cache: (brand.lower(), name.lower()) -> product_id
            product_cache: Dict[Tuple[str, str], int] = {}
            for p in db.query(Product).all():
                b_key = (p.brand or "").strip().lower()
                n_key = (p.name or "").strip().lower()
                product_cache[(b_key, n_key)] = p.id

            # 2. Existing Deduplication Cache
            # (product_id, clean_source, external_review_id)
            seen_ext_ids = set()
            for r_id, p_id, src, ext_id in db.query(Review.id, Review.product_id, Review.source, Review.external_review_id).filter(Review.external_review_id.isnot(None)).all():
                if ext_id:
                    seen_ext_ids.add((p_id, (src or "").strip().lower(), ext_id.strip()))

            # content_hash set
            seen_content_hashes = {h[0] for h in db.query(Review.content_hash).all()}

            rejection_issues: List[Dict[str, Any]] = []
            batch_reviews: List[Review] = []
            batch_metadata: List[ReviewImportMetadata] = []

            rows_processed = 0
            rows_inserted = 0
            dups_skipped = 0
            rejected_count = 0
            warning_count = 0
            row_idx = 0

            for raw_row in reader:
                row_idx += 1
                row_dict = {}
                for col_i, col_name in enumerate(detected_cols):
                    row_dict[col_name] = raw_row[col_i] if col_i < len(raw_row) else ""

                status, issues, clean_data = validate_kaggle_row(row_dict, row_idx)
                rows_processed += 1

                if status == "rejected":
                    rejected_count += 1
                    if len(rejection_issues) < 200:
                        for iss in issues:
                            rejection_issues.append({"row": row_idx, "issue": iss, "type": "rejection"})
                    continue

                if status == "warning":
                    warning_count += 1
                    if len(rejection_issues) < 200:
                        for iss in issues:
                            rejection_issues.append({"row": row_idx, "issue": iss, "type": "warning"})

                # Product Lookup / Creation
                brand_str = clean_data["brand"]
                model_str = clean_data["model"]
                prod_key = (brand_str.lower(), model_str.lower())
                product_id = product_cache.get(prod_key)

                if not product_id:
                    # Check or create product in DB
                    existing_prod = db.query(Product).filter(
                        Product.name.ilike(model_str.strip())
                    ).first()
                    if existing_prod:
                        product_id = existing_prod.id
                        product_cache[prod_key] = product_id
                    else:
                        new_prod = Product(
                            name=model_str.strip(),
                            brand=brand_str.strip() if brand_str != "Unknown" else None,
                        )
                        db.add(new_prod)
                        db.commit()
                        db.refresh(new_prod)
                        product_id = new_prod.id
                        product_cache[prod_key] = product_id

                clean_source = (clean_data["source"] or "kaggle").strip().lower()
                ext_id = clean_data["external_review_id"]
                raw_text = clean_data["raw_review_text"]
                norm_text = safe_normalize_text(raw_text)

                # Tier 3 deterministic hash
                c_hash = compute_content_hash(product_id, clean_source, raw_text)

                # Deduplication Check (Tier 1 & Tier 3)
                ext_key = (product_id, clean_source, ext_id)
                if ext_key in seen_ext_ids or c_hash in seen_content_hashes:
                    dups_skipped += 1
                    continue

                # Add to intra-job cache
                seen_ext_ids.add(ext_key)
                seen_content_hashes.add(c_hash)

                # Build Review entity
                rev = Review(
                    product_id=product_id,
                    import_job_id=job.id,
                    ingestion_method="kaggle_import",
                    external_review_id=ext_id,
                    review_title=None,
                    raw_review_text=raw_text,
                    normalized_review_text=norm_text,
                    rating=clean_data["rating"],
                    reviewer_name=clean_data["customer_name"],
                    review_date_raw=clean_data["review_date_raw"],
                    review_date=clean_data["review_date"],
                    source=clean_data["source"],
                    helpful_count=clean_data["helpful_votes"],
                    content_hash=c_hash,
                )
                batch_reviews.append(rev)

                # Build ReviewImportMetadata entity
                meta = ReviewImportMetadata(
                    import_job_id=job.id,
                    age=clean_data["age"],
                    country=clean_data["country"],
                    language=clean_data["language"],
                    verified_purchase=clean_data["verified_purchase"],
                    price_usd=clean_data["price_usd"],
                    price_local=clean_data["price_local"],
                    currency=clean_data["currency"],
                    exchange_rate_to_usd=clean_data["exchange_rate_to_usd"],
                    dataset_sentiment=clean_data["dataset_sentiment"],
                    battery_life_rating=clean_data["battery_life_rating"],
                    camera_rating=clean_data["camera_rating"],
                    performance_rating=clean_data["performance_rating"],
                    design_rating=clean_data["design_rating"],
                    display_rating=clean_data["display_rating"],
                    imported_review_length=clean_data["imported_review_length"],
                    imported_word_count=clean_data["imported_word_count"],
                )
                batch_metadata.append(meta)

                # Commit in bounded chunks
                if len(batch_reviews) >= batch_size:
                    db.add_all(batch_reviews)
                    db.flush()
                    for r, m in zip(batch_reviews, batch_metadata):
                        m.review_id = r.id
                    db.add_all(batch_metadata)

                    rows_inserted += len(batch_reviews)
                    job.rows_processed = rows_processed
                    job.rows_inserted = rows_inserted
                    job.duplicate_rows_skipped = dups_skipped
                    job.rejected_rows = rejected_count
                    job.rows_with_warnings = warning_count
                    db.commit()

                    batch_reviews.clear()
                    batch_metadata.clear()

            # Flush final batch
            if batch_reviews:
                db.add_all(batch_reviews)
                db.flush()
                for r, m in zip(batch_reviews, batch_metadata):
                    m.review_id = r.id
                db.add_all(batch_metadata)
                rows_inserted += len(batch_reviews)

            job.rows_processed = rows_processed
            job.rows_inserted = rows_inserted
            job.duplicate_rows_skipped = dups_skipped
            job.rejected_rows = rejected_count
            job.rows_with_warnings = warning_count
            job.rejection_log = json.dumps(rejection_issues)
            job.status = "COMPLETED"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"Import job {job_uuid} finished: {rows_inserted} inserted, "
                f"{dups_skipped} duplicates skipped, {rejected_count} rejected."
            )

        # Optional temporary file cleanup
        if cleanup_temp_file and file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Cleaned up temp import file {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {file_path}: {e}")

    except Exception as exc:
        logger.error(f"Import job {job_uuid} failed: {exc}", exc_info=True)
        try:
            job = db.query(ImportJob).filter(ImportJob.job_id == job_uuid).first()
            if job:
                job.status = "FAILED"
                job.error_summary = str(exc)[:500]
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as commit_exc:
            logger.error(f"Failed to record failure status for import job {job_uuid}: {commit_exc}")
    finally:
        if close_db_when_done:
            db.close()
