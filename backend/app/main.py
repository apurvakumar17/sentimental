import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.db.session import engine
from backend.app.models import Base
from backend.app.api.v1.router import api_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartreview")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized on startup
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Lightweight automatic schema migration for SQLite development DB
    try:
        with engine.begin() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info(scraping_jobs)")).fetchall()]
            if "max_pages" not in cols:
                conn.execute(text("ALTER TABLE scraping_jobs ADD COLUMN max_pages INTEGER DEFAULT 3"))
            if "max_reviews" not in cols:
                conn.execute(text("ALTER TABLE scraping_jobs ADD COLUMN max_reviews INTEGER"))
    except Exception as exc:
        logger.warning(f"Schema migration warning: {exc}")

    logger.info("Database initialized successfully.")
    yield
    logger.info("Application shutdown.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Aspect-Based Sentiment Analysis and Recommendation System — Module 1: Data Collection & Web Scraping System",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits React dev server on any port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify API and DB connectivity."""
    db_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    return {
        "status": "healthy" if db_status == "ok" else "unhealthy",
        "database": db_status,
        "module": "Module 1: Smartphone Review Data Collection and Web Scraping System"
    }

app.include_router(api_router, prefix=settings.API_V1_STR)
