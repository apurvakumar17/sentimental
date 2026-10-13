import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.db.session import get_db
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.scraping_job import ScrapingJob
from backend.app.models.import_job import ImportJob
from backend.app.models.review_import_metadata import ReviewImportMetadata

logger = logging.getLogger("smartreview.api.system")
router = APIRouter()


@router.post("/clear-database", summary="Clear all records from database")
def clear_full_database(db: Session = Depends(get_db)):
    """
    Clears all application data from the database:
    - Review import metadata
    - Reviews
    - Products
    - Scraping jobs
    - Import jobs
    Resets SQLite auto-increment sequences.
    """
    try:
        deleted_counts = {}

        # 1. Delete in foreign-key dependency order
        deleted_counts["review_import_metadata"] = db.query(ReviewImportMetadata).delete()
        deleted_counts["reviews"] = db.query(Review).delete()
        deleted_counts["products"] = db.query(Product).delete()
        deleted_counts["scraping_jobs"] = db.query(ScrapingJob).delete()
        deleted_counts["import_jobs"] = db.query(ImportJob).delete()

        db.commit()

        # 2. Reset SQLite sequence counters if table exists
        try:
            db.execute(
                text(
                    "DELETE FROM sqlite_sequence WHERE name IN "
                    "('reviews', 'products', 'scraping_jobs', 'import_jobs', 'review_import_metadata');"
                )
            )
            db.commit()
        except Exception:
            pass

        logger.info(f"Database cleared successfully: {deleted_counts}")
        return {
            "status": "success",
            "message": "Full database has been cleared successfully.",
            "deleted": deleted_counts,
        }
    except Exception as exc:
        db.rollback()
        logger.error(f"Error clearing database: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear database: {str(exc)}",
        )
