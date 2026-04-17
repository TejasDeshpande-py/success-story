"""
Banners Service Layer: Business logic for banner management
"""
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import boto3
import os
from backend.models.banner import BannerImage
from backend.models.employee import Employee

logger = logging.getLogger(__name__)


def delete_s3_url(url: str) -> None:
    """Delete an image from S3 bucket."""
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
    except Exception as exc:
        logger.warning(f"Failed to delete S3 URL: {exc}")


def get_banners(db: Session) -> list:
    """Get all banner images ordered by slot."""
    banners = db.query(BannerImage).order_by(BannerImage.slot).all()
    return [{"slot": b.slot, "image_url": b.image_url} for b in banners]


def upsert_banner(slot: int, image_url: str, db: Session, current_user: Employee) -> dict:
    """Create or update a banner at the specified slot."""
    if slot < 1 or slot > 5:
        raise HTTPException(status_code=400, detail="Slot must be between 1 and 5")
    existing = db.query(BannerImage).filter(BannerImage.slot == slot).first()
    if existing:
        delete_s3_url(existing.image_url)
        existing.image_url = image_url
        existing.updated_by = current_user.employee_id
    else:
        db.add(BannerImage(slot=slot, image_url=image_url, updated_by=current_user.employee_id))
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save banner at slot {slot}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save banner")
    return {"message": "Banner saved", "slot": slot}


def delete_banner(slot: int, db: Session, current_user: Employee) -> dict:
    """Delete a banner from the specified slot."""
    existing = db.query(BannerImage).filter(BannerImage.slot == slot).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Banner slot not found")
    delete_s3_url(existing.image_url)
    db.delete(existing)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to delete banner at slot {slot}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to delete banner")
    return {"message": "Banner removed", "slot": slot}
