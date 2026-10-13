import os
import csv
import json
import uuid
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.review import Review
from backend.app.models.product import Product
from backend.app.core.config import settings
from backend.app.core.normalization import safe_normalize_text, get_text_stats
from backend.app.services.data_quality import assess_review_record
from backend.app.schemas.dataset import (
    DataQualityConfig,
    DatasetFilterOptions,
    PreparedReviewItem,
    DatasetManifest,
)

logger = logging.getLogger("smartreview.dataset_export")

ANNOTATION_FIELDS = [
    "review_id",
    "product_id",
    "product_name",
    "brand",
    "source",
    "raw_review_text",
    "normalized_review_text",
    "rating",
    "review_date",
    "reviewer_name",
    "external_review_id",
    "review_url",
    "helpful_count",
    "char_count",
    "word_count",
    "quality_status",
    "aspect_labels",
    "sentiment_labels",
    "annotation_status",
    "annotator_notes"
]


def prepare_review_dataset(
    db: Session,
    filters: Optional[DatasetFilterOptions] = None,
    quality_config: Optional[DataQualityConfig] = None,
    limit: Optional[int] = None,
) -> Tuple[List[PreparedReviewItem], int, Dict[str, int]]:
    """
    Deterministically filters, assesses, and prepares reviews for dataset export.
    Returns: (prepared_records, total_source_examined, exclusion_breakdown).
    """
    filt = filters or DatasetFilterOptions()
    cfg = quality_config or DataQualityConfig()

    query = db.query(Review).join(Product, Review.product_id == Product.id)

    if filt.product_id is not None:
        query = query.filter(Review.product_id == filt.product_id)
    if filt.source:
        query = query.filter(Review.source.ilike(f"%{filt.source.strip()}%"))
    if filt.min_rating is not None:
        query = query.filter(Review.rating >= filt.min_rating)
    if filt.max_rating is not None:
        query = query.filter(Review.rating <= filt.max_rating)

    # Deterministic stable ordering by Review.id
    all_reviews = query.order_by(Review.id.asc()).all()
    total_source = len(all_reviews)

    seen_hashes: Dict[str, int] = {}
    seen_text_keys: Dict[Tuple[int, str], int] = {}
    exclusion_breakdown = {
        "errors": 0,
        "duplicates": 0,
        "warnings": 0,
    }

    prepared: List[PreparedReviewItem] = []

    for r in all_reviews:
        issues, status = assess_review_record(r, cfg, seen_hashes, seen_text_keys)
        issue_types = [i.issue_type for i in issues]

        # Check exclusion rules
        is_duplicate = ("exact_duplicate" in issue_types or "potential_duplicate" in issue_types)
        has_error = (status == "error")
        has_warning = (status == "warning")

        if filt.exclude_errors and has_error:
            exclusion_breakdown["errors"] += 1
            continue

        if filt.exclude_duplicates and is_duplicate:
            exclusion_breakdown["duplicates"] += 1
            continue

        if filt.exclude_warnings and has_warning and not is_duplicate:
            exclusion_breakdown["warnings"] += 1
            continue

        norm_text = r.normalized_review_text or safe_normalize_text(r.raw_review_text or "")
        stats = get_text_stats(norm_text)
        date_str = str(r.review_date) if r.review_date else (r.review_date_raw or None)

        item = PreparedReviewItem(
            review_id=r.id,
            product_id=r.product_id,
            product_name=r.product.name if r.product else "Unknown",
            brand=r.product.brand if r.product else None,
            source=r.source,
            raw_review_text=r.raw_review_text or "",
            normalized_review_text=norm_text,
            rating=r.rating,
            review_date=date_str,
            reviewer_name=r.reviewer_name,
            external_review_id=r.external_review_id,
            review_url=r.review_url,
            helpful_count=r.helpful_count or 0,
            char_count=stats["char_count"],
            word_count=stats["word_count"],
            quality_status=status,
            quality_issues=issue_types,
            aspect_labels=None,
            sentiment_labels=None,
            annotation_status="UNANNOTATED",
            annotator_notes=None
        )
        prepared.append(item)

        if limit is not None and len(prepared) >= limit:
            break

    return prepared, total_source, exclusion_breakdown


def export_dataset_to_file(
    db: Session,
    export_format: str = "csv",
    filters: Optional[DatasetFilterOptions] = None,
    quality_config: Optional[DataQualityConfig] = None,
    include_annotation_columns: bool = True,
) -> DatasetManifest:
    """
    Generates a deterministic dataset export file (CSV or JSONL) and accompanying JSON manifest.
    Files are saved strictly inside settings.EXPORTS_DIR.
    Computes an authoritative SHA-256 checksum of the exported dataset.
    """
    clean_fmt = export_format.strip().lower()
    if clean_fmt not in ("csv", "jsonl"):
        raise ValueError(f"Unsupported export format '{export_format}'. Supported formats: 'csv', 'jsonl'.")

    prepared, total_source, exclusions = prepare_review_dataset(
        db,
        filters=filters,
        quality_config=quality_config
    )

    dataset_uuid = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"smartreview_dataset_{timestamp}_{dataset_uuid}.{clean_fmt}"
    file_path = settings.EXPORTS_DIR / filename

    # Write dataset file
    if clean_fmt == "csv":
        with open(file_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            # Write header
            headers = ANNOTATION_FIELDS if include_annotation_columns else ANNOTATION_FIELDS[:-4]
            writer.writerow(headers)

            for item in prepared:
                row = [
                    item.review_id,
                    item.product_id,
                    item.product_name,
                    item.brand or "",
                    item.source,
                    item.raw_review_text,
                    item.normalized_review_text,
                    item.rating if item.rating is not None else "",
                    item.review_date or "",
                    item.reviewer_name or "",
                    item.external_review_id or "",
                    item.review_url or "",
                    item.helpful_count,
                    item.char_count,
                    item.word_count,
                    item.quality_status,
                ]
                if include_annotation_columns:
                    row.extend([
                        "", # aspect_labels
                        "", # sentiment_labels
                        item.annotation_status, # UNANNOTATED
                        ""  # annotator_notes
                    ])
                writer.writerow(row)

    elif clean_fmt == "jsonl":
        with open(file_path, mode="w", encoding="utf-8") as f:
            for item in prepared:
                data = item.model_dump()
                if not include_annotation_columns:
                    for k in ("aspect_labels", "sentiment_labels", "annotation_status", "annotator_notes"):
                        data.pop(k, None)
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

    # Compute SHA256 checksum and size
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    checksum = sha256.hexdigest()
    file_size = file_path.stat().st_size

    total_excluded = sum(exclusions.values())
    filter_dict = filters.model_dump() if filters else {}

    manifest = DatasetManifest(
        dataset_id=dataset_uuid,
        filename=filename,
        format=clean_fmt,
        generated_at=datetime.now(timezone.utc).isoformat(),
        schema_version="1.0.0",
        preprocessing_version="1.0.0",
        total_source_examined=total_source,
        total_exported_records=len(prepared),
        excluded_records=total_excluded,
        exclusion_breakdown=exclusions,
        file_size_bytes=file_size,
        sha256_checksum=checksum,
        filter_config=filter_dict,
        download_url=f"/api/v1/datasets/download/{filename}"
    )

    # Persist manifest file alongside dataset
    manifest_path = settings.EXPORTS_DIR / f"{filename}.manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, indent=2)

    logger.info(f"Exported {len(prepared)} records to {file_path} (checksum: {checksum[:8]})")
    return manifest


def list_dataset_manifests() -> List[DatasetManifest]:
    """Retrieves all previously exported dataset manifests from settings.EXPORTS_DIR."""
    manifests: List[DatasetManifest] = []
    if not settings.EXPORTS_DIR.exists():
        return manifests

    for p in sorted(settings.EXPORTS_DIR.glob("*.manifest.json"), reverse=True):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                manifests.append(DatasetManifest(**data))
        except Exception as exc:
            logger.warning(f"Could not read manifest file {p}: {exc}")

    return manifests


def get_safe_export_path(filename: str) -> Path:
    """
    Validates that a filename belongs strictly to settings.EXPORTS_DIR and prevents path traversal.
    Raises ValueError or FileNotFoundError if invalid.
    """
    # Disallow path separators in filename
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError("Invalid filename: directory traversal characters are forbidden.")

    target = (settings.EXPORTS_DIR / filename).resolve()
    exports_dir = settings.EXPORTS_DIR.resolve()

    if target.parent != exports_dir:
        raise ValueError("Path traversal attempt detected.")

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"Export file '{filename}' not found.")

    return target
