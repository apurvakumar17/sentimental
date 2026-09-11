from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.session import get_db
from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.schemas.product import ProductResponse, ProductCreate

router = APIRouter()

@router.get("", response_model=List[ProductResponse])
def get_products(
    brand: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(
        Product.id,
        Product.name,
        Product.brand,
        Product.canonical_url,
        Product.created_at,
        Product.updated_at,
        func.count(Review.id).label("review_count"),
        func.avg(Review.rating).label("average_rating")
    ).outerjoin(Review, Product.id == Review.product_id).group_by(Product.id)

    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    rows = query.all()
    results = []
    for row in rows:
        results.append(ProductResponse(
            id=row.id,
            name=row.name,
            brand=row.brand,
            canonical_url=row.canonical_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
            review_count=row.review_count or 0,
            average_rating=round(row.average_rating, 2) if row.average_rating else None
        ))
    return results

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    row = db.query(
        Product.id,
        Product.name,
        Product.brand,
        Product.canonical_url,
        Product.created_at,
        Product.updated_at,
        func.count(Review.id).label("review_count"),
        func.avg(Review.rating).label("average_rating")
    ).outerjoin(Review, Product.id == Review.product_id).filter(Product.id == product_id).group_by(Product.id).first()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductResponse(
        id=row.id,
        name=row.name,
        brand=row.brand,
        canonical_url=row.canonical_url,
        created_at=row.created_at,
        updated_at=row.updated_at,
        review_count=row.review_count or 0,
        average_rating=round(row.average_rating, 2) if row.average_rating else None
    )

@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(Product).filter(Product.name.ilike(product_in.name.strip())).first()
    if existing:
        return ProductResponse(
            id=existing.id,
            name=existing.name,
            brand=existing.brand,
            canonical_url=existing.canonical_url,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
            review_count=len(existing.reviews),
            average_rating=None
        )

    product = Product(
        name=product_in.name.strip(),
        brand=product_in.brand.strip() if product_in.brand else None,
        canonical_url=product_in.canonical_url
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductResponse(
        id=product.id,
        name=product.name,
        brand=product.brand,
        canonical_url=product.canonical_url,
        created_at=product.created_at,
        updated_at=product.updated_at,
        review_count=0,
        average_rating=None
    )
