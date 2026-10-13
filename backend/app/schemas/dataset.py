from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DataQualityConfig(BaseModel):
    """Configuration options for data-quality checks."""
    min_length: int = Field(10, ge=1, description="Minimum acceptable character length for a review")
    max_length: int = Field(5000, ge=50, description="Maximum acceptable character length for a review")
    require_rating: bool = Field(False, description="Whether rating is required (GSM Arena qualitative comments have no rating)")
    require_date: bool = Field(False, description="Whether review date is strictly required")


class DataQualityIssue(BaseModel):
    """An individual data-quality finding for a specific review."""
    review_id: int
    severity: str = Field(..., description="'error' (fatal flaw) or 'warning' (statistical/metadata anomaly)")
    issue_type: str = Field(..., description="Machine-readable code for the issue")
    message: str


class DataQualitySummary(BaseModel):
    """Aggregate data quality assessment metrics."""
    total_reviews: int
    valid_reviews: int
    clean_reviews: int
    reviews_with_warnings: int
    reviews_with_errors: int
    missing_text_count: int
    normalization_empty_count: int
    invalid_rating_count: int
    missing_product_count: int
    missing_date_count: int
    excessively_short_count: int
    excessively_long_count: int
    exact_duplicate_count: int
    potential_duplicate_count: int
    quality_score: float = Field(..., description="Score from 0.0 to 100.0 reflecting dataset readiness")
    quality_score_formula: str
    sample_issues: List[DataQualityIssue] = Field(default_factory=list)


class DatasetFilterOptions(BaseModel):
    """Criteria to filter and clean reviews during dataset generation."""
    product_id: Optional[int] = None
    source: Optional[str] = None
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    max_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    exclude_errors: bool = Field(True, description="Exclude records with fatal data quality errors")
    exclude_duplicates: bool = Field(True, description="Exclude records identified as exact duplicates")
    exclude_warnings: bool = Field(False, description="Exclude records with any quality warnings (strict mode)")


class PreparedReviewItem(BaseModel):
    """A standardized review record prepared for NLP datasets and ABSA annotation."""
    review_id: int
    product_id: int
    product_name: str
    brand: Optional[str] = None
    source: str
    raw_review_text: str
    normalized_review_text: str
    rating: Optional[float] = None
    review_date: Optional[str] = None
    reviewer_name: Optional[str] = None
    external_review_id: Optional[str] = None
    review_url: Optional[str] = None
    helpful_count: int = 0
    char_count: int = 0
    word_count: int = 0
    quality_status: str = Field("valid", description="'clean', 'valid', 'warning', or 'error'")
    quality_issues: List[str] = Field(default_factory=list)

    # Annotation-ready ABSA scaffolding (strictly unannotated / empty until real human or model annotation)
    aspect_labels: Optional[List[str]] = None
    sentiment_labels: Optional[List[str]] = None
    annotation_status: str = "UNANNOTATED"
    annotator_notes: Optional[str] = None


class DatasetPreviewResponse(BaseModel):
    """Preview response containing a limited subset of prepared dataset records."""
    total_matching: int
    preview_count: int
    records: List[PreparedReviewItem]


class DatasetExportRequest(BaseModel):
    """Request payload to trigger dataset file export."""
    format: str = Field("csv", description="Export format: 'csv' or 'jsonl'")
    filters: Optional[DatasetFilterOptions] = None
    include_annotation_columns: bool = Field(True, description="Include empty scaffolding columns for future ABSA annotations")


class DatasetManifest(BaseModel):
    """Provenance and cryptographic fingerprint for an exported dataset."""
    dataset_id: str
    filename: str
    format: str
    generated_at: str
    schema_version: str = "1.0.0"
    preprocessing_version: str = "1.0.0"
    total_source_examined: int
    total_exported_records: int
    excluded_records: int
    exclusion_breakdown: Dict[str, int]
    file_size_bytes: int
    sha256_checksum: str
    filter_config: Dict[str, Any]
    download_url: str


class DatasetExportListResponse(BaseModel):
    """Listing of previously generated dataset export manifests."""
    total: int
    items: List[DatasetManifest]
