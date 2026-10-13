from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class ReviewImportMetadata(Base):
    """
    Stores structured provenance, demographic, pricing, and Kaggle-provided aspect/sentiment
    ratings for imported reviews. Preserves all 25 dataset columns without polluting
    the core Review table.
    """
    __tablename__ = "review_import_metadata"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=True, index=True)

    # Demographic & Locale
    age = Column(Integer, nullable=True)
    country = Column(String(100), nullable=True, index=True)
    language = Column(String(50), nullable=True)
    verified_purchase = Column(Boolean, nullable=True)

    # Pricing & Currency Information
    price_usd = Column(Float, nullable=True)
    price_local = Column(String(100), nullable=True)
    currency = Column(String(20), nullable=True)
    exchange_rate_to_usd = Column(Float, nullable=True)

    # Kaggle-supplied ground truth labels (preserved separately from model predictions)
    dataset_sentiment = Column(String(50), nullable=True, index=True)
    battery_life_rating = Column(Float, nullable=True)
    camera_rating = Column(Float, nullable=True)
    performance_rating = Column(Float, nullable=True)
    design_rating = Column(Float, nullable=True)
    display_rating = Column(Float, nullable=True)

    # Imported length statistics
    imported_review_length = Column(Integer, nullable=True)
    imported_word_count = Column(Integer, nullable=True)

    review = relationship("Review", back_populates="import_metadata")
    import_job = relationship("ImportJob", back_populates="metadata_records")
