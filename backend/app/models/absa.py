from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class ReviewAnnotation(Base):
    """
    Ground-truth human aspect and sentiment annotation for a specific review.
    Annotators explicitly mark:
      - aspect: Battery, Camera, Performance, Design, Display
      - sentiment: Positive, Negative, Neutral
      - status: UNANNOTATED, IN_REVIEW, VERIFIED
    """
    __tablename__ = "review_annotations"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    aspect = Column(String(50), nullable=False, index=True)
    sentiment = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="VERIFIED", index=True)
    annotator_notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    review = relationship("Review", back_populates="annotations")

    __table_args__ = (
        Index("ix_annotations_review_aspect", "review_id", "aspect"),
    )


class ReviewPrediction(Base):
    """
    Stored output of the ABSA model for auditability and warehouse evaluation.
    Preserves:
      - aspect: detected category
      - sentiment: predicted polarity
      - confidence: model confidence score [0.0 - 1.0]
      - evidence_text: snippet or clause from the review supporting the prediction
      - model_version: tag indicating the architecture / training batch
    """
    __tablename__ = "review_predictions"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=True, index=True)
    aspect = Column(String(50), nullable=False, index=True)
    sentiment = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    evidence_text = Column(String(500), nullable=True)
    model_version = Column(String(50), nullable=False, default="absa-hybrid-v1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    review = relationship("Review", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_review_aspect", "review_id", "aspect"),
    )
