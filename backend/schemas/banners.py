from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class BannerCreate(BaseModel):
    image_url: str
    title: Optional[str] = None
    order: int = 0


class BannerResponse(BaseModel):
    banner_id: int
    image_url: str
    title: Optional[str]
    is_active: bool
    order: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True