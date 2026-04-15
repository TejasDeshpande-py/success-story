import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.models.employee import Employee
from backend.models.team import Team
from backend.models.story import SuccessStory, StoryReaction
from backend.utils import paginate
from backend.schemas.users import ApproveUserRequest
from backend.auth.security import hash_password, verify_password
import boto3
import os
from urllib.parse import urlparse
import math

logger = logging.getLogger(__name__)


def delete_s3_picture(url: str) -> None:
    """Delete picture from S3."""
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


def get_active_users(page: int, db: Session) -> dict:
    """Get active users paginated."""
    limit, offset = paginate(page)
    total = db.query(Employee).filter(Employee.status == "Active").count()
    users = db.query(Employee).filter(
        Employee.status == "Active"
    ).offset(offset).limit(limit).all()
    return {
        "users": users,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }


def get_pending_users(page: int, db: Session) -> dict:
    """Get pending users paginated."""
    limit, offset = paginate(page)
    total = db.query(Employee).filter(Employee.status == "Pending").count()
    users = db.query(Employee).filter(
        Employee.status == "Pending"
    ).offset(offset).limit(limit).all()
    return {
        "users": users,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }


def get_all_active_users(db: Session) -> list:
    """Get all active users."""
    return db.query(Employee).filter(
        Employee.status == "Active"
    ).all()


def approve_user(employee_id: int, payload: ApproveUserRequest, db: Session, current_user: Employee) -> Employee:
    """Approve pending user."""
    user = db.query(Employee).filter(
        Employee.employee_id == employee_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "Pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    if payload.role_id == 2:
        raise HTTPException(status_code=403, detail="Cannot assign Super Admin role")

    if payload.team_id is not None:
        team_exists = db.query(Team.team_id).filter(
            Team.team_id == payload.team_id
        ).scalar()
        if not team_exists:
            raise HTTPException(status_code=404, detail="Team not found")

    user.role_id = payload.role_id
    user.team_id = payload.team_id
    user.status = "Active"
    user.updated_by = current_user.employee_id
    user.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to approve user %s: %s", employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to approve user")

    db.refresh(user)
    return user


def reject_user(employee_id: int, db: Session, current_user: Employee) -> Employee:
    """Reject pending user."""
    user = db.query(Employee).filter(
        Employee.employee_id == employee_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "Pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    user.status = "Rejected"
    user.updated_by = current_user.employee_id
    user.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to reject user %s: %s", employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reject user")

    db.refresh(user)
    return user


def delete_user(employee_id: int, db: Session, current_user: Employee) -> dict:
    """Delete user and cascade related data."""
    user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.employee_id == current_user.employee_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if user.role_id == 2:
        raise HTTPException(status_code=403, detail="Cannot delete a Super Admin")
    
    try:
        # Update stories where user was the updater
        db.query(SuccessStory).filter(
            SuccessStory.updated_by == employee_id
        ).update({"updated_by": None}, synchronize_session=False)
        
        # Get stories related to user
        story_ids = db.query(SuccessStory.story_id).filter(
            (SuccessStory.created_by == employee_id) | (SuccessStory.story_for == employee_id)
        ).all()
        story_ids = [row.story_id for row in story_ids]
        
        # Delete reactions for those stories
        if story_ids:
            db.query(StoryReaction).filter(
                StoryReaction.story_id.in_(story_ids)
            ).delete(synchronize_session=False)
            # Delete stories
            db.query(SuccessStory).filter(
                SuccessStory.story_id.in_(story_ids)
            ).delete(synchronize_session=False)
        
        # Delete user
        db.delete(user)
        db.commit()
    except Exception as exc:
        logger.error("Failed to delete user %s: %s", employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")
    
    return {"message": "User deleted successfully"}


def update_employee_team(employee_id: int, team_id: int | None, db: Session, current_user: Employee) -> dict:
    """Update employee's team assignment."""
    user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if team_id:
        team = db.query(Team).filter(Team.team_id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
    
    user.team_id = team_id
    user.updated_by = current_user.employee_id
    user.updated_at = datetime.now(timezone.utc)
    
    try:
        db.commit()
        db.refresh(user)
    except Exception as exc:
        logger.error("Failed to update team for user %s: %s", employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update team")
    
    return {"message": "Team updated successfully", "team_id": user.team_id}


def update_me(payload, db: Session, current_user: Employee) -> Employee:
    """Update current user's profile."""
    if payload.picture:
        delete_s3_picture(current_user.picture)
        current_user.picture = payload.picture
    
    if payload.new_password:
        if not payload.old_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if not verify_password(payload.old_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        if verify_password(payload.new_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="New password cannot be same as current password")
        current_user.password_hash = hash_password(payload.new_password)
    
    current_user.updated_at = datetime.now(timezone.utc)
    
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as exc:
        logger.error("Failed to update profile for user %s: %s", current_user.employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update profile")
    
    return current_user
