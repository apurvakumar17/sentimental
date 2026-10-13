import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.session import get_db
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.absa import ReviewPrediction
from backend.app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    AspectDefinition,
    ProductSummaryItem,
    ComparisonRequest,
    ComparisonResponse,
    ProductScoreDetailResponse,
)
from backend.app.services.recommendation_service import recommendation_engine

logger = logging.getLogger("smartreview.recommendation_api")

router = APIRouter()


@router.post("", response_model=RecommendationResponse, summary="Get personalized smartphone recommendations")
def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """
    Ranks eligible smartphones according to user budget, brand preferences,
    and priority aspects (Battery, Camera, Performance, Design, Display).
    Uses Bayesian credibility-smoothed review sentiment scores.
    """
    try:
        return recommendation_engine.recommend(db=db, request=request)
    except Exception as exc:
        logger.error(f"Recommendation generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(exc)}"
        )


@router.get("/aspects", response_model=List[AspectDefinition], summary="Get supported smartphone aspects")
def get_aspect_definitions():
    """
    Returns the 5 canonical smartphone aspects with definitions, domain keywords,
    and default importance weights.
    """
    return recommendation_engine.get_aspect_definitions()


@router.get("/products", response_model=List[ProductSummaryItem], summary="List catalog products and recommendation eligibility")
def list_recommendation_products(db: Session = Depends(get_db)):
    """
    Returns all catalog products with representative USD prices, total reviews count,
    and ABSA evidence availability. Useful for comparison selectors.
    """
    prices_map = recommendation_engine.get_product_prices_map(db)
    
    # Review counts
    rev_count_rows = db.query(Review.product_id, func.count(Review.id)).group_by(Review.product_id).all()
    rev_counts = {r[0]: int(r[1]) for r in rev_count_rows}

    # Prediction counts
    pred_count_rows = (
        db.query(Review.product_id, func.count(ReviewPrediction.id))
        .join(ReviewPrediction, Review.id == ReviewPrediction.review_id)
        .group_by(Review.product_id)
        .all()
    )
    pred_counts = {r[0]: int(r[1]) for r in pred_count_rows}

    products = db.query(Product).order_by(Product.name.asc()).all()
    results = []

    for p in products:
        p_evidence = pred_counts.get(p.id, 0)
        results.append(
            ProductSummaryItem(
                product_id=p.id,
                product_name=p.name,
                brand=p.brand,
                avg_price_usd=prices_map.get(p.id),
                total_reviews=rev_counts.get(p.id, 0),
                has_predictions=p_evidence > 0,
                evidence_count=p_evidence,
            )
        )

    return results


@router.post("/compare", response_model=ComparisonResponse, summary="Compare 2 to 5 smartphones side by side")
def compare_smartphones(
    request: ComparisonRequest,
    db: Session = Depends(get_db),
):
    """
    Compares selected smartphones across price, aspect scores, evidence volume,
    sentiment distribution, and strengths/weaknesses.
    """
    unique_ids = list(dict.fromkeys(request.product_ids))
    if len(unique_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comparison requires at least 2 distinct product IDs."
        )

    try:
        return recommendation_engine.compare(db=db, product_ids=unique_ids)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        logger.error(f"Comparison failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare products: {str(exc)}"
        )


@router.get("/products/{product_id}/scores", response_model=ProductScoreDetailResponse, summary="Get detailed aspect scores for a product")
def get_product_score_detail(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns aspect scores, evidence counts, positive/neutral/negative breakdown,
    and sample review snippets for an individual smartphone.
    """
    try:
        return recommendation_engine.get_product_score_detail(db=db, product_id=product_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        logger.error(f"Failed to get score details for product {product_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve score details: {str(exc)}"
        )


@router.post("/sync-predictions", summary="Precompute ABSA predictions for warehouse reviews")
def sync_warehouse_predictions(
    limit_per_product: int = Query(50, ge=5, le=200, description="Max reviews to analyze per product"),
    db: Session = Depends(get_db),
):
    """
    Precomputes ABSA predictions for warehouse reviews using the trained model
    to populate review_predictions across all catalog devices.
    """
    try:
        return recommendation_engine.sync_warehouse_predictions(db=db, limit_per_product=limit_per_product)
    except Exception as exc:
        logger.error(f"Prediction sync failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync predictions: {str(exc)}"
        )
