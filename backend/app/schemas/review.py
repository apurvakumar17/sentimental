from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator

class RawReviewIn(BaseModel):
    product_name: str = Field(..., min_length=1)
    brand: Optional[str] = None
    product_url: Optional[str] = None
    external_review_id: Optional[str] = None
    review_title: Optional[str] = None
    raw_review_text: str = Field(..., min_length=1)
    normalized_review_text: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    reviewer_name: Optional[str] = None
    review_date_raw: Optional[str] = None
    review_date: Optional[date] = None
    source: str = Field(default="demo_catalog")
    review_url: Optional[str] = None
    helpful_count: int = Field(default=0, ge=0)

    @field_validator("raw_review_text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Review text cannot be empty or only whitespace")
        return trimmed

    @field_validator("review_url")
    @classmethod
    def validate_review_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        trimmed = v.strip()
        if not trimmed:
            return None
        valid_schemes = ("http://", "https://", "demo://", "gsmarena://")
        if not any(trimmed.lower().startswith(s) for s in valid_schemes):
            raise ValueError(f"Review URL must start with one of: {valid_schemes}")
        return trimmed

class ReviewResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    scraping_job_id: Optional[int] = None
    external_review_id: Optional[str] = None
    review_title: Optional[str] = None
    raw_review_text: str
    normalized_review_text: Optional[str] = None
    rating: Optional[float] = None
    reviewer_name: Optional[str] = None
    review_date_raw: Optional[str] = None
    review_date: Optional[date] = None
    source: str
    review_url: Optional[str] = None
    helpful_count: int
    content_hash: str
    scraped_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ReviewListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List[ReviewResponse]
