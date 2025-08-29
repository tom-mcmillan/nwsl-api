from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., ge=0)
    quantity: int = Field(..., ge=0)
    is_active: bool = True


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ItemInDB(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemResponse(ItemInDB):
    pass


class PaginatedItems(BaseModel):
    items: list[ItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int