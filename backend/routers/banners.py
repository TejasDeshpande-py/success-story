from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.employee import Employee
from backend.auth.dependencies import require_hr_or_admin
from pydantic import BaseModel
from backend.services import banners_service

router = APIRouter(prefix="/banners", tags=["Banners"])

class BannerUpsertRequest(BaseModel):
    slot: int
    image_url: str

class BannerDeleteRequest(BaseModel):
    slot: int

@router.get("/")
def get_banners(db: Session = Depends(get_db)):
    return banners_service.get_banners(db)

@router.post("/")
def upsert_banner(payload: BannerUpsertRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return banners_service.upsert_banner(payload.slot, payload.image_url, db, current_user)

@router.delete("/")
def delete_banner(payload: BannerDeleteRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return banners_service.delete_banner(payload.slot, db)
