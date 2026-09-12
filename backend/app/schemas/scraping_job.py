from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ScrapingJobCreate(BaseModel):
    target_url: str = Field(..., min_length=1, description="Target URL (demo://, http://, https://)")
    scraper_type: str = Field(default="demo", description="Registered scraper adapter key")
    product_name: Optional[str] = None
    brand: Optional[str] = None
    max_pages: Optional[int] = Field(default=5, ge=1, description="Max pages to scrape (>= 1, or None/null for unlimited)")
    max_reviews: Optional[int] = Field(default=None, ge=1, le=5000, description="Optional cap on total reviews (1-5000)")
    delay_seconds: float = Field(default=1.0, ge=0.0, le=10.0, description="Polite inter-page delay in seconds (0-10)")

    @field_validator("target_url")
    @classmethod
    def validate_target_url(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Target URL cannot be empty or whitespace")
        valid_schemes = ("demo://", "http://", "https://", "demo", "gsmarena://")
        if not any(trimmed.lower().startswith(s) for s in valid_schemes):
            raise ValueError(f"Target URL must start with one of: {valid_schemes}")
        return trimmed

    @field_validator("scraper_type")
    @classmethod
    def validate_scraper_type(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Scraper type cannot be empty")
        return trimmed

class ScrapingJobResponse(BaseModel):
    id: int
    job_id: str
    target_url: str
    scraper_type: str
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    status: str
    max_pages: Optional[int] = None
    max_reviews: Optional[int] = None
    pages_attempted: int
    successful_pages: int
    failed_pages: int
    reviews_discovered: int
    inserted_reviews: int
    duplicate_reviews: int
    error_log: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ScrapingJobListResponse(BaseModel):
    total: int
    items: List[ScrapingJobResponse]
