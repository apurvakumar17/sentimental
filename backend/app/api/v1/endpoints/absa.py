import logging
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.review import Review
from backend.app.models.absa import ReviewAnnotation, ReviewPrediction
from backend.app.schemas.absa import (
    ABSAPredictRequest,
    ABSAPredictResponse,
    ABSAModelStatus,
    ABSATrainRequest,
    ABSATrainResponse,
    ABSAMetricsResponse,
    AnnotationCreateRequest,
    AnnotationResponse,
)
from backend.app.services.absa_service import absa_engine

logger = logging.getLogger("smartreview.absa_api")

router = APIRouter()


@router.post("/predict", response_model=ABSAPredictResponse, summary="Predict aspects and sentiment for raw text")
def predict_raw_text(request: ABSAPredictRequest):
    """
    Analyzes supplied review text, extracts smartphone aspects (Battery, Camera, Performance, Design, Display),
    and predicts aspect-level sentiment (Positive, Negative, Neutral).
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Review text cannot be empty.")

    aspect_results = absa_engine.predict_text(request.text)
    return ABSAPredictResponse(
        text=request.text,
        detected_aspects=aspect_results,
        aspects_count=len(aspect_results),
        has_aspects=len(aspect_results) > 0,
        model_version=absa_engine.metadata.get("model_version", "absa-hybrid-v1.0") if absa_engine.metadata else "absa-hybrid-v1.0",
    )


@router.post("/predict/{review_id}", response_model=ABSAPredictResponse, summary="Analyze an existing database review")
def predict_existing_review(
    review_id: int,
    save_prediction: bool = Query(True, description="Whether to store predictions in the review_predictions table"),
    db: Session = Depends(get_db),
):
    """
    Performs Aspect-Based Sentiment Analysis on an existing review from the database warehouse.
    Optionally saves the inference results to the database without modifying raw review text.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with ID {review_id} not found."
        )

    try:
        response = absa_engine.predict_review(db=db, review_id=review_id, save_prediction=save_prediction)
        return response
    except Exception as exc:
        logger.error(f"Error predicting review {review_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference error: {str(exc)}")


@router.get("/status", response_model=ABSAModelStatus, summary="Check model readiness and annotation counts")
def get_model_status(db: Session = Depends(get_db)):
    """
    Returns model training status, architecture info, available aspects/sentiments,
    and verified human ground-truth annotation counts.
    """
    return absa_engine.get_status(db=db)


@router.post("/train", response_model=ABSATrainResponse, summary="Train or retrain the ABSA model")
def train_model(
    request: Optional[ABSATrainRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Trains the ABSA model using verified annotations and/or the seed smartphone review dataset.
    Splits data reproducibly into train/test sets and computes comprehensive evaluation metrics.
    """
    req = request or ABSATrainRequest()
    try:
        result = absa_engine.train(
            db=db,
            test_size=req.test_size,
            random_state=req.random_state,
            include_seed_dataset=req.include_seed_dataset,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error(f"Training failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(exc)}")


@router.get("/metrics", response_model=ABSAMetricsResponse, summary="Get held-out evaluation metrics")
def get_evaluation_metrics():
    """
    Returns latest evaluation metrics from the held-out test set:
    Macro F1, Accuracy, per-class metrics, and confusion matrix.
    """
    return absa_engine.get_metrics()


@router.post("/annotate/{review_id}", response_model=List[AnnotationResponse], summary="Save human annotations for a review")
def annotate_review(
    review_id: int,
    request: AnnotationCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Allows researchers or annotators to assign verified ground-truth aspect-sentiment labels
    to an existing database review without fabricating labels or corrupting raw text.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review with ID {review_id} not found.")

    created_or_updated: List[ReviewAnnotation] = []

    for item in request.annotations:
        existing = (
            db.query(ReviewAnnotation)
            .filter(
                ReviewAnnotation.review_id == review_id,
                ReviewAnnotation.aspect == item.aspect
            )
            .first()
        )
        if existing:
            existing.sentiment = item.sentiment
            existing.status = item.status
            existing.annotator_notes = item.annotator_notes
            created_or_updated.append(existing)
        else:
            new_anno = ReviewAnnotation(
                review_id=review_id,
                aspect=item.aspect,
                sentiment=item.sentiment,
                status=item.status,
                annotator_notes=item.annotator_notes,
            )
            db.add(new_anno)
            created_or_updated.append(new_anno)

    db.commit()
    for anno in created_or_updated:
        db.refresh(anno)

    return created_or_updated


@router.get("/annotations", summary="List verified or pending review annotations")
def list_annotations(
    review_id: Optional[int] = Query(None, description="Filter by review ID"),
    aspect: Optional[str] = Query(None, description="Filter by aspect"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (VERIFIED, UNANNOTATED, IN_REVIEW)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(ReviewAnnotation)
    if review_id is not None:
        query = query.filter(ReviewAnnotation.review_id == review_id)
    if aspect:
        query = query.filter(ReviewAnnotation.aspect == aspect)
    if status_filter:
        query = query.filter(ReviewAnnotation.status == status_filter.upper())

    total = query.count()
    offset = (page - 1) * page_size
    records = query.order_by(ReviewAnnotation.id.desc()).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
        "items": [
            {
                "id": r.id,
                "review_id": r.review_id,
                "aspect": r.aspect,
                "sentiment": r.sentiment,
                "status": r.status,
                "annotator_notes": r.annotator_notes,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in records
        ],
    }


@router.get("/predictions/{review_id}", summary="Get stored predictions for a review")
def get_review_predictions(review_id: int, db: Session = Depends(get_db)):
    """
    Returns previously computed and stored model predictions for a given review.
    """
    preds = db.query(ReviewPrediction).filter(ReviewPrediction.review_id == review_id).all()
    return [
        {
            "id": p.id,
            "review_id": p.review_id,
            "aspect": p.aspect,
            "sentiment": p.sentiment,
            "confidence": p.confidence,
            "evidence_text": p.evidence_text,
            "model_version": p.model_version,
            "created_at": p.created_at,
        }
        for p in preds
    ]
