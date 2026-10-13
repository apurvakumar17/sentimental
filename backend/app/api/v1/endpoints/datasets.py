import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.data_quality import evaluate_dataset_quality
from backend.app.services.dataset_export import (
    prepare_review_dataset,
    export_dataset_to_file,
    list_dataset_manifests,
    get_safe_export_path,
)
from backend.app.schemas.dataset import (
    DataQualityConfig,
    DataQualitySummary,
    DatasetFilterOptions,
    DatasetPreviewResponse,
    DatasetExportRequest,
    DatasetManifest,
    DatasetExportListResponse,
)

logger = logging.getLogger("smartreview.api.datasets")
router = APIRouter()


@router.post("/quality", response_model=DataQualitySummary, summary="Run read-only data quality evaluation")
def assess_data_quality(
    product_id: Optional[int] = Query(None, description="Optional filter by product ID"),
    config: Optional[DataQualityConfig] = None,
    db: Session = Depends(get_db)
):
    """
    Evaluates dataset quality rules across collected reviews:
    - Identifies missing texts, empty normalizations, invalid ratings
    - Tracks exact and potential duplicates
    - Calculates transparent Quality Score [0.0 - 100.0]
    - Read-only: never modifies or deletes reviews
    """
    try:
        return evaluate_dataset_quality(db=db, product_id=product_id, config=config)
    except Exception as exc:
        logger.error(f"Error assessing data quality: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess dataset quality: {str(exc)}"
        )


@router.post("/preview", response_model=DatasetPreviewResponse, summary="Preview prepared dataset records")
def preview_dataset(
    filters: Optional[DatasetFilterOptions] = None,
    limit: int = Query(10, ge=1, le=50, description="Max preview records to return"),
    db: Session = Depends(get_db)
):
    """
    Previews prepared reviews applying deterministic filtering and exclusion rules.
    Shows raw review text alongside safe normalized text and annotation scaffolding.
    """
    try:
        prepared, total_source, exclusions = prepare_review_dataset(
            db=db,
            filters=filters,
            limit=limit
        )
        return DatasetPreviewResponse(
            total_matching=total_source - sum(exclusions.values()),
            preview_count=len(prepared),
            records=prepared
        )
    except Exception as exc:
        logger.error(f"Error generating dataset preview: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview dataset: {str(exc)}"
        )


@router.post("/export", response_model=DatasetManifest, status_code=status.HTTP_201_CREATED, summary="Export dataset to CSV or JSONL")
def export_dataset(
    req: DatasetExportRequest,
    db: Session = Depends(get_db)
):
    """
    Generates a deterministic dataset file (CSV or JSONL) in the exports directory.
    Computes an authoritative SHA-256 checksum and returns export manifest metadata.
    """
    try:
        manifest = export_dataset_to_file(
            db=db,
            export_format=req.format,
            filters=req.filters,
            include_annotation_columns=req.include_annotation_columns
        )
        return manifest
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Error exporting dataset: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export dataset: {str(exc)}"
        )


@router.get("/exports", response_model=DatasetExportListResponse, summary="List previous dataset exports")
def list_exports():
    """Returns provenance manifests of all previously exported dataset files."""
    try:
        manifests = list_dataset_manifests()
        return DatasetExportListResponse(
            total=len(manifests),
            items=manifests
        )
    except Exception as exc:
        logger.error(f"Error listing dataset exports: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list dataset exports: {str(exc)}"
        )


@router.get("/download/{filename}", summary="Download exported dataset file safely")
def download_export(filename: str):
    """
    Safely downloads a generated dataset file from the exports directory.
    Strictly prevents directory traversal and restricts downloads to verified files.
    """
    try:
        file_path = get_safe_export_path(filename)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(fnf))

    media_type = "text/csv" if filename.endswith(".csv") else "application/x-ndjson"
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )
