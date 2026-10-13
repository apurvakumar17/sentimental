import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.review import Review
from backend.app.models.product import Product
from backend.app.core.normalization import safe_normalize_text, get_text_stats
from backend.app.schemas.dataset import (
    DataQualityConfig,
    DataQualityIssue,
    DataQualitySummary,
    PreparedReviewItem,
)

logger = logging.getLogger("smartreview.data_quality")


def assess_review_record(
    review: Review,
    config: DataQualityConfig,
    seen_hashes: Dict[str, int],
    seen_text_keys: Dict[Tuple[int, str], int],
) -> Tuple[List[DataQualityIssue], str]:
    """
    Assesses a single review record against configured data-quality rules.
    Returns (issues_list, overall_status) where status is 'clean', 'valid', 'warning', or 'error'.
    """
    issues: List[DataQualityIssue] = []

    # 1. Inspect Raw Review Text
    raw_text = review.raw_review_text or ""
    if not raw_text.strip():
        issues.append(DataQualityIssue(
            review_id=review.id,
            severity="error",
            issue_type="missing_text",
            message="Raw review text is missing, empty, or whitespace only."
        ))

    # 2. Inspect Normalized Text
    norm_text = safe_normalize_text(raw_text)
    if raw_text.strip() and not norm_text:
        issues.append(DataQualityIssue(
            review_id=review.id,
            severity="error",
            issue_type="normalization_empty",
            message="Review text became empty after Unicode NFKC and HTML sanitization."
        ))

    stats = get_text_stats(norm_text or raw_text)
    char_count = stats["char_count"]
    word_count = stats["word_count"]

    # 3. Product Association
    if not review.product_id or not review.product:
        issues.append(DataQualityIssue(
            review_id=review.id,
            severity="error",
            issue_type="missing_product",
            message=f"Review is missing valid product relationship (product_id={review.product_id})."
        ))
    elif not review.product.brand:
        issues.append(DataQualityIssue(
            review_id=review.id,
            severity="warning",
            issue_type="missing_product_metadata",
            message=f"Associated product '{review.product.name}' is missing brand metadata."
        ))

    # 4. Source Check
    if not review.source or not review.source.strip():
        issues.append(DataQualityIssue(
            review_id=review.id,
            severity="error",
            issue_type="missing_source",
            message="Review record has no source attribute."
        ))

    # 5. Rating Check
    if review.rating is not None:
        if not (0.0 <= review.rating <= 5.0):
            issues.append(DataQualityIssue(
                review_id=review.id,
                severity="error",
                issue_type="invalid_rating",
                message=f"Rating value {review.rating} is outside valid bounds [0.0, 5.0]."
            ))
    elif config.require_rating:
        issues.append(DataQualityIssue(
            review_id=review.id,
            severity="warning",
            issue_type="missing_rating",
            message="Numeric rating is null (typical for qualitative GSM Arena comments)."
        ))

    # 6. Length Boundaries (Warnings)
    if norm_text:
        if word_count < 3 or char_count < config.min_length:
            issues.append(DataQualityIssue(
                review_id=review.id,
                severity="warning",
                issue_type="excessively_short",
                message=f"Review is excessively short ({word_count} words, {char_count} chars < {config.min_length})."
            ))
        elif char_count > config.max_length:
            issues.append(DataQualityIssue(
                review_id=review.id,
                severity="warning",
                issue_type="excessively_long",
                message=f"Review length ({char_count} chars) exceeds maximum threshold ({config.max_length})."
            ))

    # 7. Date Check
    if not review.review_date and not review.review_date_raw:
        if config.require_date:
            issues.append(DataQualityIssue(
                review_id=review.id,
                severity="warning",
                issue_type="missing_date",
                message="Review date is missing."
            ))

    # 8. Author Metadata
    if not review.reviewer_name or review.reviewer_name.strip().lower() in ("anonymous", "unknown", "nan", ""):
        issues.append(DataQualityIssue(
            review_id=review.id,
            severity="warning",
            issue_type="missing_author",
            message="Reviewer author is anonymous or unrecorded."
        ))

    # 9. Duplication Analysis (In-memory tracking across query)
    c_hash = review.content_hash
    if c_hash:
        if c_hash in seen_hashes:
            orig_id = seen_hashes[c_hash]
            issues.append(DataQualityIssue(
                review_id=review.id,
                severity="warning",
                issue_type="exact_duplicate",
                message=f"Exact duplicate detected; shares content_hash with review ID {orig_id}."
            ))
        else:
            seen_hashes[c_hash] = review.id

    # Potential Duplicate (Identical normalized text for same product, differing external metadata)
    if review.product_id and norm_text:
        text_key = (review.product_id, norm_text.lower())
        if text_key in seen_text_keys:
            orig_id = seen_text_keys[text_key]
            if orig_id != review.id and not any(i.issue_type == "exact_duplicate" for i in issues):
                issues.append(DataQualityIssue(
                    review_id=review.id,
                    severity="warning",
                    issue_type="potential_duplicate",
                    message=f"Potential duplicate; identical normalized text matches review ID {orig_id}."
                ))
        else:
            seen_text_keys[text_key] = review.id

    # Determine Overall Quality Status
    has_errors = any(i.severity == "error" for i in issues)
    has_warnings = any(i.severity == "warning" for i in issues)

    if has_errors:
        status = "error"
    elif has_warnings:
        status = "warning"
    else:
        status = "clean"

    return issues, status


def evaluate_dataset_quality(
    db: Session,
    product_id: Optional[int] = None,
    config: Optional[DataQualityConfig] = None,
    max_sample_issues: int = 50,
) -> DataQualitySummary:
    """
    Executes a comprehensive, read-only data quality evaluation across reviews in the database.
    Does not delete or alter any records.
    Calculates transparent metrics and an overall Quality Score [0.0 - 100.0].
    """
    cfg = config or DataQualityConfig()

    query = db.query(Review)
    if product_id is not None:
        query = query.filter(Review.product_id == product_id)

    # Order deterministically by review id
    reviews = query.order_by(Review.id.asc()).all()
    total_reviews = len(reviews)

    if total_reviews == 0:
        return DataQualitySummary(
            total_reviews=0,
            valid_reviews=0,
            clean_reviews=0,
            reviews_with_warnings=0,
            reviews_with_errors=0,
            missing_text_count=0,
            normalization_empty_count=0,
            invalid_rating_count=0,
            missing_product_count=0,
            missing_date_count=0,
            excessively_short_count=0,
            excessively_long_count=0,
            exact_duplicate_count=0,
            potential_duplicate_count=0,
            quality_score=100.0,
            quality_score_formula="Score = 100.0 (empty dataset)",
            sample_issues=[]
        )

    seen_hashes: Dict[str, int] = {}
    seen_text_keys: Dict[Tuple[int, str], int] = {}

    all_issues: List[DataQualityIssue] = []
    error_review_ids = set()
    warning_review_ids = set()

    missing_text_count = 0
    normalization_empty_count = 0
    invalid_rating_count = 0
    missing_product_count = 0
    missing_date_count = 0
    excessively_short_count = 0
    excessively_long_count = 0
    exact_duplicate_count = 0
    potential_duplicate_count = 0

    for r in reviews:
        issues, status = assess_review_record(r, cfg, seen_hashes, seen_text_keys)
        all_issues.extend(issues)

        for iss in issues:
            if iss.severity == "error":
                error_review_ids.add(r.id)
                if iss.issue_type == "missing_text":
                    missing_text_count += 1
                elif iss.issue_type == "normalization_empty":
                    normalization_empty_count += 1
                elif iss.issue_type == "invalid_rating":
                    invalid_rating_count += 1
                elif iss.issue_type == "missing_product":
                    missing_product_count += 1
            elif iss.severity == "warning":
                warning_review_ids.add(r.id)
                if iss.issue_type == "missing_date":
                    missing_date_count += 1
                elif iss.issue_type == "excessively_short":
                    excessively_short_count += 1
                elif iss.issue_type == "excessively_long":
                    excessively_long_count += 1
                elif iss.issue_type == "exact_duplicate":
                    exact_duplicate_count += 1
                elif iss.issue_type == "potential_duplicate":
                    potential_duplicate_count += 1

    reviews_with_errors = len(error_review_ids)
    # Reviews that have warnings but no fatal errors
    reviews_with_warnings = len(warning_review_ids - error_review_ids)
    valid_reviews = total_reviews - reviews_with_errors
    clean_reviews = total_reviews - len(error_review_ids | warning_review_ids)

    # Documented Quality Score Calculation:
    # Formula: Quality Score = 100.0 - Penalty
    # where Penalty = ((errors * 1.0) + (warnings * 0.15) + (duplicates * 0.25)) / total * 100.0
    penalty = (
        (reviews_with_errors * 1.0) +
        (reviews_with_warnings * 0.15) +
        (exact_duplicate_count * 0.25)
    ) / total_reviews * 100.0

    quality_score = round(max(0.0, min(100.0, 100.0 - penalty)), 1)
    formula_desc = (
        "Quality Score = max(0, min(100, 100 - ((errors * 1.0 + warnings * 0.15 + duplicates * 0.25) / total * 100)))"
    )

    return DataQualitySummary(
        total_reviews=total_reviews,
        valid_reviews=valid_reviews,
        clean_reviews=clean_reviews,
        reviews_with_warnings=reviews_with_warnings,
        reviews_with_errors=reviews_with_errors,
        missing_text_count=missing_text_count,
        normalization_empty_count=normalization_empty_count,
        invalid_rating_count=invalid_rating_count,
        missing_product_count=missing_product_count,
        missing_date_count=missing_date_count,
        excessively_short_count=excessively_short_count,
        excessively_long_count=excessively_long_count,
        exact_duplicate_count=exact_duplicate_count,
        potential_duplicate_count=potential_duplicate_count,
        quality_score=quality_score,
        quality_score_formula=formula_desc,
        sample_issues=all_issues[:max_sample_issues]
    )
