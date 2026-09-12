import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    target_url = Column(String(500), nullable=False)
    scraper_type = Column(String(50), nullable=False, default="demo")
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED

    max_pages = Column(Integer, nullable=True)
    max_reviews = Column(Integer, nullable=True)

    pages_attempted = Column(Integer, default=0, nullable=False)
    successful_pages = Column(Integer, default=0, nullable=False)
    failed_pages = Column(Integer, default=0, nullable=False)
    reviews_discovered = Column(Integer, default=0, nullable=False)
    inserted_reviews = Column(Integer, default=0, nullable=False)
    duplicate_reviews = Column(Integer, default=0, nullable=False)

    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="scraping_jobs")
    reviews = relationship("Review", back_populates="scraping_job")
