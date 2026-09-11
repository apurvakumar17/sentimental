from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    canonical_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    review_count: int = 0
    average_rating: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
