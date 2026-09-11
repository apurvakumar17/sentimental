import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.db.session import SessionLocal, engine
from backend.app.models import Base
from backend.app.services.job_runner import execute_scraping_job
from backend.app.models.scraping_job import ScrapingJob
from backend.app.models.product import Product
from backend.app.models.review import Review

def seed():
    print("[1/3] Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    existing_reviews = db.query(Review).count()
    if existing_reviews > 0:
        print(f"Database already contains {existing_reviews} reviews across {db.query(Product).count()} products.")
        db.close()
        return

    print("[2/3] Seeding demo smartphone reviews...")
    devices = [
        ("demo://iphone-15-pro", "Apple iPhone 15 Pro", "Apple"),
        ("demo://galaxy-s24-ultra", "Samsung Galaxy S24 Ultra", "Samsung"),
        ("demo://pixel-8-pro", "Google Pixel 8 Pro", "Google"),
    ]

    import uuid
    for target_url, name, brand in devices:
        job_id = str(uuid.uuid4())
        job = ScrapingJob(
            job_id=job_id,
            target_url=target_url,
            scraper_type="demo",
            status="PENDING"
        )
        db.add(job)
        db.commit()

        print(f"  -> Scraping reviews for {name} ({brand})...")
        execute_scraping_job(
            job_uuid=job_id,
            target_url=target_url,
            scraper_type="demo",
            product_name=name,
            brand=brand,
            max_pages=3,
            delay_seconds=0.0,
            db_session=db
        )

    print("[3/3] Demo seeding complete!")
    print(f"Total Products: {db.query(Product).count()}")
    print(f"Total Reviews : {db.query(Review).count()}")
    print(f"Total Jobs    : {db.query(ScrapingJob).count()}")
    db.close()

if __name__ == "__main__":
    seed()
