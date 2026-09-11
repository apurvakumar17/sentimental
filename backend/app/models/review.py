from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Date, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    scraping_job_id = Column(Integer, ForeignKey("scraping_jobs.id"), nullable=True, index=True)

    external_review_id = Column(String(150), nullable=True, index=True)
    review_title = Column(String(300), nullable=True)
    raw_review_text = Column(Text, nullable=False)
    normalized_review_text = Column(Text, nullable=True)
    rating = Column(Float, nullable=True)
    reviewer_name = Column(String(150), nullable=True)
    review_date_raw = Column(String(100), nullable=True)
    review_date = Column(Date, nullable=True)
    source = Column(String(100), nullable=False, default="demo_catalog", index=True)
    review_url = Column(String(500), nullable=True, index=True)
    helpful_count = Column(Integer, default=0, nullable=False)

    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    scraped_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="reviews")
    scraping_job = relationship("ScrapingJob", back_populates="reviews")

    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_review_content_hash"),
        Index("ix_reviews_prod_ext_id", "product_id", "source", "external_review_id"),
        Index("ix_reviews_prod_url", "product_id", "review_url"),
    )
