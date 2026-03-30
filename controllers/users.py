from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from model import Employee, Team, SuccessStory
from schemas import ApproveUserRequest
from security import hash_password, verify_password
import boto3, os
from urllib.parse import urlparse

def delete_s3_picture(url: str):
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


def get_active_users(page: int, db: Session, paginate):
    import math
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

def get_pending_users(page: int, db: Session, paginate):
    import math
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

def get_all_active_users(db: Session):
    return db.query(Employee).filter(
        Employee.status == "Active"
    ).all()

def approve_user(employee_id: int, payload: ApproveUserRequest, db: Session, current_user: Employee):
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
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to approve user")

    db.refresh(user)
    return user

def reject_user(employee_id: int, db: Session, current_user: Employee):
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
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reject user")

    db.refresh(user)
    return user
def delete_user(employee_id: int, db: Session, current_user: Employee):
    user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.employee_id == current_user.employee_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if user.role_id == 2:
        raise HTTPException(status_code=403, detail="Cannot delete a Super Admin")
    if current_user.role_id == 1 and user.role_id == 2:
        raise HTTPException(status_code=403, detail="HR cannot delete a Super Admin")
    try:
        # Null out updated_by references in stories updated by this user
        db.query(SuccessStory).filter(
            SuccessStory.updated_by == employee_id
        ).update({"updated_by": None}, synchronize_session=False)
        # Delete stories created by or for this user
        db.query(SuccessStory).filter(
            (SuccessStory.created_by == employee_id) | (SuccessStory.story_for == employee_id)
        ).delete(synchronize_session=False)
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")
    return {"message": "User deleted successfully"}

def update_employee_team(employee_id: int, payload: dict, db: Session, current_user: Employee):
    user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    team_id = payload.get("team_id")
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
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update team")
    return {"message": "Team updated successfully", "team_id": user.team_id}

def update_me(payload: dict, db: Session, current_user: Employee):
    if "picture" in payload and payload["picture"]:
        delete_s3_picture(current_user.picture)
        current_user.picture = payload["picture"]
    if "new_password" in payload and payload["new_password"]:
        if not payload.get("old_password"):
            raise HTTPException(status_code=400, detail="Current password is required")
        if not verify_password(payload["old_password"], current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        if verify_password(payload["new_password"], current_user.password_hash):
            raise HTTPException(status_code=400, detail="New password cannot be same as current password")
        if len(payload["new_password"]) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
        if not any(c.isupper() for c in payload["new_password"]):
            raise HTTPException(status_code=400, detail="New password must contain an uppercase letter")
        if not any(c.isdigit() for c in payload["new_password"]):
            raise HTTPException(status_code=400, detail="New password must contain a number")
        current_user.password_hash = hash_password(payload["new_password"])
    current_user.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(current_user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update profile")
    return current_user