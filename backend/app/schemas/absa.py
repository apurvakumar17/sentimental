from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

ASPECTS_LIST = ["Battery", "Camera", "Performance", "Design", "Display"]
SENTIMENTS_LIST = ["Positive", "Negative", "Neutral"]

AspectType = Literal["Battery", "Camera", "Performance", "Design", "Display"]
SentimentType = Literal["Positive", "Negative", "Neutral"]
AnnotationStatusType = Literal["UNANNOTATED", "IN_REVIEW", "VERIFIED"]


class AspectSentimentResult(BaseModel):
    aspect: AspectType = Field(..., description="Target smartphone aspect category")
    sentiment: SentimentType = Field(..., description="Predicted sentiment polarity towards the aspect")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    evidence_text: Optional[str] = Field(None, description="Extracted clause or sentence supporting this prediction")


class ABSAPredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Raw review text to analyze")
    save_prediction: bool = Field(False, description="Whether to persist predictions in database if review_id is known")


class ABSAPredictResponse(BaseModel):
    text: str
    detected_aspects: List[AspectSentimentResult] = Field(default_factory=list)
    aspects_count: int = 0
    model_version: str = "absa-hybrid-v1"
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    review_id: Optional[int] = None
    has_aspects: bool = False


class ABSAModelStatus(BaseModel):
    model_name: str = "SmartReview Aspect-Based Sentiment Analyzer"
    model_version: str = "absa-hybrid-v1"
    is_trained: bool = False
    model_type: str = "TF-IDF + Context Clause Valence Hybrid Classifier"
    available_aspects: List[str] = Field(default_factory=lambda: list(ASPECTS_LIST))
    available_sentiments: List[str] = Field(default_factory=lambda: list(SENTIMENTS_LIST))
    verified_annotations_count: int = 0
    total_annotations_count: int = 0
    last_trained_at: Optional[datetime] = None
    artifacts_exist: bool = False


class ABSATrainRequest(BaseModel):
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="Fraction of annotated data to hold out for evaluation")
    random_state: int = Field(42, description="Random seed for reproducible dataset splitting")
    include_seed_dataset: bool = Field(True, description="Whether to combine verified database annotations with the gold seed benchmark")


class ABSATrainResponse(BaseModel):
    status: str = "success"
    message: str
    model_version: str
    training_samples: int
    test_samples: int
    aspect_metrics: Dict[str, Any] = Field(default_factory=dict)
    sentiment_metrics: Dict[str, Any] = Field(default_factory=dict)
    overall_macro_f1: float
    overall_accuracy: float
    trained_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ABSAMetricsResponse(BaseModel):
    has_metrics: bool = False
    model_version: Optional[str] = None
    test_samples_count: Optional[int] = None
    aspect_detection_metrics: Optional[Dict[str, Any]] = None
    sentiment_classification_metrics: Optional[Dict[str, Any]] = None
    per_class_sentiment_metrics: Optional[Dict[str, Any]] = None
    confusion_matrix: Optional[Dict[str, Any]] = None
    last_evaluated_at: Optional[datetime] = None
    data_split_info: Optional[str] = None


class AnnotationItem(BaseModel):
    aspect: AspectType
    sentiment: SentimentType
    status: AnnotationStatusType = "VERIFIED"
    annotator_notes: Optional[str] = None


class AnnotationCreateRequest(BaseModel):
    annotations: List[AnnotationItem]


class AnnotationResponse(BaseModel):
    id: int
    review_id: int
    aspect: str
    sentiment: str
    status: str
    annotator_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
