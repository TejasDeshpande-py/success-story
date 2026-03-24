from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from model import Employee, Team
from schemas import ApproveUserRequest


def get_active_users(page: int, db: Session, paginate):
    limit, offset = paginate(page)
    return db.query(Employee).filter(
        Employee.status == "Active"
    ).offset(offset).limit(limit).all()




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