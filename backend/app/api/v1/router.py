from fastapi import APIRouter
from backend.app.api.v1.endpoints import products, reviews, jobs, datasets, imports, system, absa, recommendations

api_router = APIRouter()
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Scraping Jobs"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets & Quality"])
api_router.include_router(imports.router, prefix="/imports", tags=["Dataset Imports"])
api_router.include_router(system.router, prefix="/system", tags=["System Maintenance"])
api_router.include_router(absa.router, prefix="/absa", tags=["Aspect-Based Sentiment Analysis"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Product Recommendations"])
