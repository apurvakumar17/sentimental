import csv
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dateutil import parser as date_parser

logger = logging.getLogger("smartreview.kaggle_validator")

# Exact canonical 25 columns required in the Kaggle CSV
KAGGLE_REQUIRED_COLUMNS = [
    "review_id",
    "customer_name",
    "age",
    "brand",
    "model",
    "price_usd",
    "price_local",
    "currency",
    "exchange_rate_to_usd",
    "rating",
    "review_text",
    "sentiment",
    "country",
    "language",
    "review_date",
    "verified_purchase",
    "battery_life_rating",
    "camera_rating",
    "performance_rating",
    "design_rating",
    "display_rating",
    "review_length",
    "word_count",
    "helpful_votes",
    "source",
]

ACCEPTED_SENTIMENT_LABELS = {"positive", "negative", "neutral", "mixed"}


def parse_boolean_value(val: Optional[str]) -> Optional[bool]:
    """Parses text boolean expressions safely."""
    if val is None:
        return None
    cleaned = str(val).strip().lower()
    if cleaned in ("true", "1", "yes", "t"):
        return True
    if cleaned in ("false", "0", "no", "f"):
        return False
    return None


def parse_float_value(val: Optional[str]) -> Optional[float]:
    """Safely extracts a float value or returns None if unparseable/blank."""
    if val is None:
        return None
    cleaned = str(val).strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int_value(val: Optional[str]) -> Optional[int]:
    """Safely extracts an integer or returns None if unparseable/blank."""
    if val is None:
        return None
    cleaned = str(val).strip()
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def validate_kaggle_row(
    row: Dict[str, str],
    row_num: int,
) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Validates a single Kaggle CSV row.
    Returns:
      (status, issues_list, parsed_clean_data)
      where status is 'valid', 'warning', or 'rejected'.
    """
    issues: List[str] = []
    is_rejected = False

    raw_text = (row.get("review_text") or "").strip()
    if not raw_text:
        issues.append(f"Row {row_num}: Fatal - 'review_text' is blank or missing.")
        is_rejected = True

    model_name = (row.get("model") or "").strip()
    brand_name = (row.get("brand") or "").strip()
    if not model_name and not brand_name:
        issues.append(f"Row {row_num}: Fatal - Both 'model' and 'brand' are missing.")
        is_rejected = True

    ext_id = (row.get("review_id") or "").strip()
    if not ext_id:
        issues.append(f"Row {row_num}: Fatal - 'review_id' is missing.")
        is_rejected = True

    # Rating validation (Scale 0.0 - 5.0)
    rating_raw = row.get("rating")
    rating_val = parse_float_value(rating_raw)
    if rating_raw and str(rating_raw).strip() and rating_val is None:
        issues.append(f"Row {row_num}: Fatal - Unparseable overall 'rating' value '{rating_raw}'.")
        is_rejected = True
    elif rating_val is not None:
        if not (0.0 <= rating_val <= 5.0):
            issues.append(f"Row {row_num}: Warning - 'rating' {rating_val} is outside [0.0, 5.0] bounds.")

    # Aspect ratings validation (Documented Scale: 1.0 - 5.0)
    aspect_fields = [
        "battery_life_rating",
        "camera_rating",
        "performance_rating",
        "design_rating",
        "display_rating",
    ]
    parsed_aspects = {}
    for af in aspect_fields:
        aval_raw = row.get(af)
        aval = parse_float_value(aval_raw)
        if aval_raw and str(aval_raw).strip() and aval is None:
            issues.append(f"Row {row_num}: Warning - Unparseable aspect rating '{af}'='{aval_raw}'.")
        elif aval is not None and not (1.0 <= aval <= 5.0):
            issues.append(f"Row {row_num}: Warning - Aspect rating '{af}'={aval} is outside [1.0, 5.0] bounds.")
        parsed_aspects[af] = aval

    # Sentiment label check
    sentiment_raw = (row.get("sentiment") or "").strip()
    if sentiment_raw and sentiment_raw.lower() not in ACCEPTED_SENTIMENT_LABELS:
        issues.append(f"Row {row_num}: Warning - Non-standard sentiment label '{sentiment_raw}'.")

    # Date parsing
    date_raw = (row.get("review_date") or "").strip()
    parsed_date = None
    if date_raw:
        try:
            parsed_date = date_parser.parse(date_raw, fuzzy=True).date()
        except Exception:
            issues.append(f"Row {row_num}: Warning - Unparseable 'review_date' string '{date_raw}'.")

    # Text length warnings
    if raw_text and len(raw_text) < 10:
        issues.append(f"Row {row_num}: Warning - Review length ({len(raw_text)} chars) is excessively short (<10c).")

    # Customer and numerical parsing
    age_val = parse_int_value(row.get("age"))
    price_usd_val = parse_float_value(row.get("price_usd"))
    exchange_val = parse_float_value(row.get("exchange_rate_to_usd"))
    helpful_val = parse_int_value(row.get("helpful_votes")) or 0
    verified_val = parse_boolean_value(row.get("verified_purchase"))
    review_len_val = parse_int_value(row.get("review_length"))
    word_count_val = parse_int_value(row.get("word_count"))

    # Determine overall row status
    if is_rejected:
        status = "rejected"
    elif issues:
        status = "warning"
    else:
        status = "valid"

    clean_data = {
        "external_review_id": ext_id,
        "customer_name": (row.get("customer_name") or "").strip() or "Anonymous",
        "age": age_val,
        "brand": brand_name or "Unknown",
        "model": model_name or "Smartphone",
        "price_usd": price_usd_val,
        "price_local": (row.get("price_local") or "").strip() or None,
        "currency": (row.get("currency") or "").strip() or None,
        "exchange_rate_to_usd": exchange_val,
        "rating": rating_val,
        "raw_review_text": raw_text,
        "dataset_sentiment": sentiment_raw or None,
        "country": (row.get("country") or "").strip() or None,
        "language": (row.get("language") or "").strip() or None,
        "review_date": parsed_date,
        "review_date_raw": date_raw or None,
        "verified_purchase": verified_val,
        "battery_life_rating": parsed_aspects.get("battery_life_rating"),
        "camera_rating": parsed_aspects.get("camera_rating"),
        "performance_rating": parsed_aspects.get("performance_rating"),
        "design_rating": parsed_aspects.get("design_rating"),
        "display_rating": parsed_aspects.get("display_rating"),
        "imported_review_length": review_len_val,
        "imported_word_count": word_count_val,
        "helpful_votes": helpful_val,
        "source": (row.get("source") or "").strip() or "Kaggle",
    }

    return status, issues, clean_data


def validate_and_preview_csv(
    file_path: Path,
    sample_limit: int = 10,
    scan_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Validates CSV headers and provides a preview report without touching the database.
    Reads via streaming iterator to handle up to 50,000 rows with bounded memory usage.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found at {file_path}")

    file_size_bytes = file_path.stat().st_size

    # Open with utf-8-sig to automatically strip UTF-8 BOM if present
    with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return {
                "filename": file_path.name,
                "file_size_bytes": file_size_bytes,
                "detected_columns": [],
                "missing_columns": KAGGLE_REQUIRED_COLUMNS,
                "extra_columns": [],
                "is_schema_valid": False,
                "total_rows_scanned": 0,
                "sample_rows": [],
                "valid_row_count": 0,
                "warning_row_count": 0,
                "rejected_row_count": 0,
                "sample_validation_issues": [{"row": 0, "issue": "File is empty"}],
            }

        # Normalize header strings
        detected_columns = [h.strip().lower() for h in raw_headers]
        required_set = set(KAGGLE_REQUIRED_COLUMNS)
        detected_set = set(detected_columns)

        missing_columns = [col for col in KAGGLE_REQUIRED_COLUMNS if col not in detected_set]
        extra_columns = [col for col in detected_columns if col not in required_set]
        is_schema_valid = len(missing_columns) == 0

        sample_rows = []
        validation_issues = []
        valid_count = 0
        warning_count = 0
        rejected_count = 0
        row_idx = 0

        for raw_row in reader:
            row_idx += 1
            if scan_limit is not None and row_idx > scan_limit:
                break

            # Pad or trim row to match detected header length
            row_dict = {}
            for col_i, col_name in enumerate(detected_columns):
                row_dict[col_name] = raw_row[col_i] if col_i < len(raw_row) else ""

            status, issues, clean_data = validate_kaggle_row(row_dict, row_idx)

            if status == "rejected":
                rejected_count += 1
            elif status == "warning":
                warning_count += 1
            else:
                valid_count += 1

            if issues and len(validation_issues) < 50:
                for iss in issues:
                    validation_issues.append({"row": row_idx, "issue": iss, "severity": status})

            if len(sample_rows) < sample_limit:
                sample_rows.append({
                    "csv_row": row_idx,
                    "review_id": row_dict.get("review_id", ""),
                    "brand": clean_data.get("brand", ""),
                    "model": clean_data.get("model", ""),
                    "source": clean_data.get("source", ""),
                    "rating": clean_data.get("rating"),
                    "sentiment": clean_data.get("dataset_sentiment"),
                    "review_text": clean_data.get("raw_review_text", "")[:120] + ("..." if len(clean_data.get("raw_review_text", "")) > 120 else ""),
                    "status": status,
                })

        return {
            "filename": file_path.name,
            "file_size_bytes": file_size_bytes,
            "detected_columns": detected_columns,
            "missing_columns": missing_columns,
            "extra_columns": extra_columns,
            "is_schema_valid": is_schema_valid,
            "total_rows_scanned": row_idx,
            "sample_rows": sample_rows,
            "valid_row_count": valid_count,
            "warning_row_count": warning_count,
            "rejected_row_count": rejected_count,
            "sample_validation_issues": validation_issues,
        }
