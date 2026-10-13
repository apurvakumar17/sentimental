import json
import uuid
import math
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.import_job import ImportJob
from backend.app.schemas.import_job import (
    CSVPreviewResponse,
    ImportJobResponse,
    ImportJobListResponse,
    ImportJobErrorsResponse,
)
from backend.app.services.kaggle_csv_validator import validate_and_preview_csv
from backend.app.services.kaggle_importer import execute_kaggle_import_job

router = APIRouter()


@router.post("/preview", response_model=CSVPreviewResponse)
async def preview_csv_import(
    file: UploadFile = File(...),
):
    """
    Validates CSV headers and provides a preview report of valid, warning,
    and rejected rows without inserting any records into the database.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported for dataset import.")

    # Save to temp location for streaming inspection
    temp_filename = f"preview_{uuid.uuid4().hex[:8]}.csv"
    temp_path = settings.IMPORTS_DIR / temp_filename

    try:
        content = await file.read()
        max_bytes = settings.MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum allowed upload size ({settings.MAX_IMPORT_FILE_SIZE_MB}MB)."
            )

        temp_path.write_bytes(content)
        preview_data = validate_and_preview_csv(temp_path, sample_limit=10, scan_limit=1000)
        return CSVPreviewResponse(**preview_data)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV preview: {str(exc)}")
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


@router.post("", response_model=ImportJobResponse, status_code=201)
async def create_import_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Creates an asynchronous batch import job for a Kaggle CSV dataset.
    Stores the uploaded file in controlled temp storage and enqueues background processing.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported for dataset import.")

    content = await file.read()
    max_bytes = settings.MAX_IMPORT_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed upload size ({settings.MAX_IMPORT_FILE_SIZE_MB}MB)."
        )

    # Sanitize and generate safe server-side storage filename
    job_uuid = str(uuid.uuid4())
    stored_filename = f"import_{job_uuid[:8]}_{uuid.uuid4().hex[:6]}.csv"
    stored_path = settings.IMPORTS_DIR / stored_filename
    stored_path.write_bytes(content)

    job = ImportJob(
        job_id=job_uuid,
        original_filename=file.filename[:250],
        server_filepath=str(stored_path),
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Launch background worker
    background_tasks.add_task(
        execute_kaggle_import_job,
        job_uuid=job_uuid,
        file_path=stored_path,
        batch_size=500,
        cleanup_temp_file=False,
    )

    return ImportJobResponse.model_validate(job)


@router.get("", response_model=ImportJobListResponse)
def list_import_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lists recent dataset import jobs with status and row counts."""
    jobs = db.query(ImportJob).order_by(ImportJob.id.desc()).limit(limit).all()
    return ImportJobListResponse(
        total=len(jobs),
        items=[ImportJobResponse.model_validate(j) for j in jobs]
    )


@router.get("/{job_id}", response_model=ImportJobResponse)
def get_import_job(
    job_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves live status and progress metrics for a specific import job."""
    job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return ImportJobResponse.model_validate(job)


@router.get("/{job_id}/errors", response_model=ImportJobErrorsResponse)
def get_import_job_errors(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Returns paginated row-level validation rejections and warnings for an import job."""
    job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found.")

    all_errors = []
    if job.rejection_log:
        try:
            all_errors = json.loads(job.rejection_log)
        except Exception:
            all_errors = []

    total_errors = len(all_errors)
    start_idx = (page - 1) * page_size
    paged_errors = all_errors[start_idx : start_idx + page_size]

    return ImportJobErrorsResponse(
        job_id=job_id,
        total_errors=total_errors,
        page=page,
        page_size=page_size,
        errors=paged_errors,
    )
