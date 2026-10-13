import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class ImportJob(Base):
    """
    Tracks asynchronous CSV dataset import batches.
    Maintains row-level insertion, duplicate, and rejection statistics.
    """
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    original_filename = Column(String(255), nullable=False)
    server_filepath = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED

    total_rows = Column(Integer, default=0, nullable=False)
    rows_processed = Column(Integer, default=0, nullable=False)
    rows_inserted = Column(Integer, default=0, nullable=False)
    duplicate_rows_skipped = Column(Integer, default=0, nullable=False)
    rejected_rows = Column(Integer, default=0, nullable=False)
    rows_with_warnings = Column(Integer, default=0, nullable=False)

    error_summary = Column(Text, nullable=True)
    rejection_log = Column(Text, nullable=True)  # JSON-encoded array of row-level errors

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    reviews = relationship("Review", back_populates="import_job")
    metadata_records = relationship("ReviewImportMetadata", back_populates="import_job")
