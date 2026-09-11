from fastapi import APIRouter
from backend.app.api.v1.endpoints import products, reviews, jobs

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Scraping Jobs"])
