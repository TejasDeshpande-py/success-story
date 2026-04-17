from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.employee import Employee
from backend.models.banner import BannerImage
from backend.auth.dependencies import require_hr_or_admin
from pydantic import BaseModel
import boto3
import os
from urllib.parse import urlparse

router = APIRouter(prefix="/banners", tags=["Banners"])


class BannerUpsertRequest(BaseModel):
    slot: int
    image_url: str


class BannerDeleteRequest(BaseModel):
    slot: int


def delete_s3_url(url: str):
    if not url:
        return
    try:
        key = urlparse(url).path.lstrip('/')
        s3 = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        s3.delete_object(Bucket=os.getenv("AWS_BUCKET_NAME"), Key=key)
    except Exception:
        pass


@router.get("/")
def get_banners(db: Session = Depends(get_db)):
    banners = db.query(BannerImage).order_by(BannerImage.slot).all()
    return [{"slot": b.slot, "image_url": b.image_url} for b in banners]


@router.post("/")
def upsert_banner(payload: BannerUpsertRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    if payload.slot < 1 or payload.slot > 5:
        raise HTTPException(status_code=400, detail="Slot must be between 1 and 5")
    existing = db.query(BannerImage).filter(BannerImage.slot == payload.slot).first()
    if existing:
        delete_s3_url(existing.image_url)
        existing.image_url = payload.image_url
        existing.updated_by = current_user.employee_id
    else:
        db.add(BannerImage(slot=payload.slot, image_url=payload.image_url, updated_by=current_user.employee_id))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save banner")
    return {"message": "Banner saved", "slot": payload.slot}


@router.delete("/")
def delete_banner(payload: BannerDeleteRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    existing = db.query(BannerImage).filter(BannerImage.slot == payload.slot).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Banner slot not found")
    delete_s3_url(existing.image_url)
    db.delete(existing)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete banner")
    return {"message": "Banner removed", "slot": payload.slot}

