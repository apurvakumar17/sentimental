from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


ASPECTS_LIST = ["Battery", "Camera", "Performance", "Design", "Display"]


class AspectDefinition(BaseModel):
    aspect: str
    description: str
    keywords: List[str]
    default_weight: float = 1.0


class AspectScoreItem(BaseModel):
    aspect: str
    score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Aspect score on 0-100 scale (None if unavailable)")
    is_available: bool = Field(True, description="Whether sufficient review evidence exists for this aspect")
    evidence_count: int = Field(0, description="Total unique reviews providing evidence for this aspect")
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    raw_sentiment_ratio: Optional[float] = None
    confidence_weighted_evidence: float = 0.0


class ProductRecommendationItem(BaseModel):
    rank: int
    product_id: int
    product_name: str
    brand: Optional[str] = None
    price_usd: Optional[float] = None
    price_display: Optional[str] = None
    overall_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Weighted recommendation score (None if uncalculable)")
    coverage_ratio: float = Field(..., ge=0.0, le=1.0, description="Fraction of user-selected priorities with available review evidence")
    aspect_scores: Dict[str, AspectScoreItem] = Field(default_factory=dict)
    total_reviews_count: int = 0
    total_predictions_count: int = 0
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    explanation: str
    data_limitations: List[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    min_price: Optional[float] = Field(None, ge=0.0, description="Minimum budget in USD")
    max_price: Optional[float] = Field(None, ge=0.0, description="Maximum budget in USD")
    brands: Optional[List[str]] = Field(None, description="Preferred smartphone brands (empty/None for all)")
    priorities: List[str] = Field(
        default_factory=lambda: ["Camera", "Battery", "Performance"],
        description="Priority aspects ordered by importance"
    )
    priority_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Explicit numerical weights for aspects (e.g. {'Camera': 3.0, 'Battery': 2.0})"
    )
    min_evidence_count: Optional[int] = Field(
        1,
        ge=0,
        description="Minimum total aspect review evidence required"
    )
    limit: int = Field(10, ge=1, le=50, description="Maximum number of recommendations to return")


class RecommendationResponse(BaseModel):
    total_eligible_products: int
    matched_products_count: int
    applied_budget_filter: Optional[str] = None
    applied_brand_filter: Optional[List[str]] = None
    priorities_evaluated: List[str]
    recommendations: List[ProductRecommendationItem] = Field(default_factory=list)
    empty_state_reason: Optional[str] = None


class ProductSummaryItem(BaseModel):
    product_id: int
    product_name: str
    brand: Optional[str] = None
    avg_price_usd: Optional[float] = None
    total_reviews: int = 0
    has_predictions: bool = False
    evidence_count: int = 0


class ProductComparisonItem(BaseModel):
    product_id: int
    product_name: str
    brand: Optional[str] = None
    price_usd: Optional[float] = None
    price_display: Optional[str] = None
    overall_score: Optional[float] = None
    aspect_scores: Dict[str, AspectScoreItem] = Field(default_factory=dict)
    total_reviews_count: int = 0
    total_evidence_count: int = 0
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class ComparisonRequest(BaseModel):
    product_ids: List[int] = Field(..., min_length=2, max_length=5, description="2 to 5 product IDs to compare")


class ComparisonResponse(BaseModel):
    products: List[ProductComparisonItem]
    aspect_winners: Dict[str, Optional[str]] = Field(default_factory=dict, description="Top-performing phone per aspect")
    summary: str


class ProductScoreDetailResponse(BaseModel):
    product_id: int
    product_name: str
    brand: Optional[str] = None
    price_usd: Optional[float] = None
    total_reviews: int
    aspect_scores: Dict[str, AspectScoreItem]
    strengths: List[str]
    weaknesses: List[str]
    sample_evidence: Dict[str, List[str]] = Field(default_factory=dict)
