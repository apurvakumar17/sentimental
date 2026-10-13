from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class CSVPreviewResponse(BaseModel):
    filename: str
    file_size_bytes: int
    detected_columns: List[str]
    missing_columns: List[str]
    extra_columns: List[str]
    is_schema_valid: bool
    total_rows_scanned: int
    sample_rows: List[Dict[str, Any]]
    valid_row_count: int
    warning_row_count: int
    rejected_row_count: int
    sample_validation_issues: List[Dict[str, Any]] = Field(default_factory=list)


class ImportJobResponse(BaseModel):
    id: int
    job_id: str
    original_filename: str
    status: str
    total_rows: int
    rows_processed: int
    rows_inserted: int
    duplicate_rows_skipped: int
    rejected_rows: int
    rows_with_warnings: int
    error_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportJobListResponse(BaseModel):
    total: int
    items: List[ImportJobResponse]


class ImportJobErrorsResponse(BaseModel):
    job_id: str
    total_errors: int
    page: int
    page_size: int
    errors: List[Dict[str, Any]]
