import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.db.session import get_db
from backend.app.models.review import Review
from backend.app.models.product import Product
from backend.app.schemas.review import ReviewResponse, ReviewListResponse

router = APIRouter()

@router.get("", response_model=ReviewListResponse)
def list_reviews(
    product_id: Optional[int] = Query(None, description="Filter by product ID"),
    source: Optional[str] = Query(None, description="Filter by review source"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Minimum rating"),
    max_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Maximum rating"),
    q: Optional[str] = Query(None, description="Keyword search in title or text"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    query = db.query(Review).join(Product, Review.product_id == Product.id)

    if product_id is not None:
        query = query.filter(Review.product_id == product_id)
    if source:
        query = query.filter(Review.source.ilike(f"%{source}%"))
    if min_rating is not None:
        query = query.filter(Review.rating >= min_rating)
    if max_rating is not None:
        query = query.filter(Review.rating <= max_rating)
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Review.raw_review_text.ilike(search_pattern),
                Review.review_title.ilike(search_pattern),
                Product.name.ilike(search_pattern)
            )
        )

    total = query.count()
    pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    records = query.order_by(Review.id.desc()).offset(offset).limit(page_size).all()

    items = []
    for r in records:
        items.append(ReviewResponse(
            id=r.id,
            product_id=r.product_id,
            product_name=r.product.name if r.product else None,
            product_brand=r.product.brand if r.product else None,
            scraping_job_id=r.scraping_job_id,
            external_review_id=r.external_review_id,
            review_title=r.review_title,
            raw_review_text=r.raw_review_text,
            normalized_review_text=r.normalized_review_text,
            rating=r.rating,
            reviewer_name=r.reviewer_name,
            review_date_raw=r.review_date_raw,
            review_date=r.review_date,
            source=r.source,
            review_url=r.review_url,
            helpful_count=r.helpful_count,
            content_hash=r.content_hash,
            scraped_timestamp=r.scraped_timestamp
        ))

    return ReviewListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=items
    )

@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: int, db: Session = Depends(get_db)):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewResponse(
        id=r.id,
        product_id=r.product_id,
        product_name=r.product.name if r.product else None,
        product_brand=r.product.brand if r.product else None,
        scraping_job_id=r.scraping_job_id,
        external_review_id=r.external_review_id,
        review_title=r.review_title,
        raw_review_text=r.raw_review_text,
        normalized_review_text=r.normalized_review_text,
        rating=r.rating,
        reviewer_name=r.reviewer_name,
        review_date_raw=r.review_date_raw,
        review_date=r.review_date,
        source=r.source,
        review_url=r.review_url,
        helpful_count=r.helpful_count,
        content_hash=r.content_hash,
        scraped_timestamp=r.scraped_timestamp
    )
