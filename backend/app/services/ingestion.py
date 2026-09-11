import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.scraping_job import ScrapingJob
from backend.app.schemas.review import RawReviewIn
from backend.app.core.normalization import safe_normalize_text

logger = logging.getLogger("smartreview.ingestion")

def compute_content_hash(product_id: int, source_or_text: str, raw_text: Optional[str] = None) -> str:
    """
    Tier 3 Fallback Hash: Deterministic SHA256 computed from:
    (product_id + normalized_source + safe_normalized_text.lower())
    Supports both:
      - compute_content_hash(product_id, source, text)
      - compute_content_hash(product_id, text) [defaults source to 'demo_catalog']
    """
    if raw_text is None:
        source = "demo_catalog"
        text = source_or_text
    else:
        source = source_or_text
        text = raw_text

    clean_source = (source or "demo_catalog").strip().lower()
    clean_text = safe_normalize_text(text).lower()
    payload = f"{product_id}:{clean_source}:{clean_text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def get_or_create_product(db: Session, name: str, brand: Optional[str] = None, canonical_url: Optional[str] = None) -> Product:
    clean_name = name.strip()
    product = db.query(Product).filter(Product.name.ilike(clean_name)).first()
    if not product:
        product = Product(
            name=clean_name,
            brand=brand.strip() if brand else None,
            canonical_url=canonical_url
        )
        db.add(product)
        db.commit()
        db.refresh(product)
    return product

def parse_iso_date(raw_date_str: Optional[str]):
    if not raw_date_str:
        return None
    try:
        parsed = date_parser.parse(raw_date_str, fuzzy=True)
        return parsed.date()
    except Exception:
        return None

def check_is_duplicate(
    db: Session,
    product_id: int,
    source: str,
    external_review_id: Optional[str],
    review_url: Optional[str],
    content_hash: str,
    seen_ext_ids: set,
    seen_urls: set,
    seen_hashes: set
) -> bool:
    """
    Executes the 3-tier deduplication check against both the in-flight batch
    and persisted database records:
      - Tier 1: Source review ID (external_review_id) for the product and source
      - Tier 2: Canonical review URL (review_url) for the product
      - Tier 3: Deterministic content hash (product_id + source + normalized_text)
    """
    clean_source = (source or "default").strip().lower()

    # Tier 1: External Review ID
    if external_review_id:
        ext_key = (product_id, clean_source, external_review_id.strip())
        if ext_key in seen_ext_ids:
            logger.debug(f"[Dedup Tier 1] Intra-batch duplicate external_id={external_review_id}")
            return True
        existing_ext = db.query(Review.id).filter(
            Review.product_id == product_id,
            Review.source == clean_source,
            Review.external_review_id == external_review_id.strip()
        ).first()
        if existing_ext:
            logger.debug(f"[Dedup Tier 1] Database duplicate external_id={external_review_id}")
            return True

    # Tier 2: Review URL
    if review_url:
        clean_url = review_url.strip()
        url_key = (product_id, clean_url)
        if url_key in seen_urls:
            logger.debug(f"[Dedup Tier 2] Intra-batch duplicate review_url={clean_url}")
            return True
        existing_url = db.query(Review.id).filter(
            Review.product_id == product_id,
            Review.review_url == clean_url
        ).first()
        if existing_url:
            logger.debug(f"[Dedup Tier 2] Database duplicate review_url={clean_url}")
            return True

    # Tier 3: Deterministic Content Hash Fallback
    if content_hash in seen_hashes:
        logger.debug(f"[Dedup Tier 3] Intra-batch duplicate content_hash={content_hash[:8]}")
        return True
    existing_hash = db.query(Review.id).filter(Review.content_hash == content_hash).first()
    if existing_hash:
        logger.debug(f"[Dedup Tier 3] Database duplicate content_hash={content_hash[:8]}")
        return True

    return False

def ingest_review_batch(
    db: Session,
    reviews: List[RawReviewIn],
    job: ScrapingJob,
    default_product_id: Optional[int] = None,
    max_reviews_remaining: Optional[int] = None
) -> Tuple[int, int]:
    """
    Validates, applies safe normalization, deduplicates via 3-tier strategy,
    and persists review records. Respects optional max_reviews limit.
    Returns (inserted_count, duplicate_count).
    """
    inserted = 0
    duplicates = 0

    # In-memory tracking for intra-batch duplicate detection
    seen_ext_ids = set()
    seen_urls = set()
    seen_hashes = set()

    for item in reviews:
        # Check max_reviews limit
        if max_reviews_remaining is not None and inserted >= max_reviews_remaining:
            logger.info(f"Max review limit reached for job {job.job_id}. Stopping batch ingestion.")
            break

        # Determine product association
        product_id = default_product_id
        if not product_id:
            prod = get_or_create_product(db, name=item.product_name, brand=item.brand, canonical_url=item.product_url)
            product_id = prod.id

        clean_source = (item.source or "demo_catalog").strip().lower()

        # Compute safe normalized text (Unicode NFKC, collapsed spaces, no NLP)
        normalized_text = safe_normalize_text(item.raw_review_text)

        # Tier 3 Hash
        c_hash = compute_content_hash(product_id, clean_source, item.raw_review_text)

        # Run 3-tier deduplication check
        if check_is_duplicate(
            db=db,
            product_id=product_id,
            source=clean_source,
            external_review_id=item.external_review_id,
            review_url=item.review_url,
            content_hash=c_hash,
            seen_ext_ids=seen_ext_ids,
            seen_urls=seen_urls,
            seen_hashes=seen_hashes
        ):
            duplicates += 1
            continue

        # Record into batch tracking sets
        if item.external_review_id:
            seen_ext_ids.add((product_id, clean_source, item.external_review_id.strip()))
        if item.review_url:
            seen_urls.add((product_id, item.review_url.strip()))
        seen_hashes.add(c_hash)

        # Parse date if available
        clean_date = item.review_date or parse_iso_date(item.review_date_raw)

        review_model = Review(
            product_id=product_id,
            scraping_job_id=job.id,
            external_review_id=item.external_review_id.strip() if item.external_review_id else None,
            review_title=item.review_title.strip() if item.review_title else None,
            raw_review_text=item.raw_review_text,
            normalized_review_text=normalized_text,
            rating=item.rating,
            reviewer_name=item.reviewer_name.strip() if item.reviewer_name else None,
            review_date_raw=item.review_date_raw,
            review_date=clean_date,
            source=clean_source,
            review_url=item.review_url.strip() if item.review_url else None,
            helpful_count=item.helpful_count,
            content_hash=c_hash,
            scraped_timestamp=datetime.now(timezone.utc)
        )
        db.add(review_model)
        inserted += 1

    db.commit()
    return inserted, duplicates
