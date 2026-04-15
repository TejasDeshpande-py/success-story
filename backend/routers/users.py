from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, field_validator
from backend.db.session import get_db
from backend.models.employee import Employee
from backend.schemas.users import UserResponse, ApproveUserRequest
from backend.services import users_service
from backend.auth.dependencies import require_hr_or_admin, get_current_user

class UpdateMeRequest(BaseModel):
    picture: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("new_password")
    def password_rules(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("New password must contain an uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("New password must contain a number")
        return v

class UpdateTeamRequest(BaseModel):
    team_id: Optional[int] = None

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
def get_all_users(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_service.get_active_users(page, db)

@router.get("/me", response_model=UserResponse)
def get_me(db=Depends(get_db), current_user=Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UpdateMeRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return users_service.update_me(payload, db, current_user)

@router.get("/pending")
def get_pending_users(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_service.get_pending_users(page, db)

@router.get("/all", response_model=List[UserResponse])
def get_all_users_list(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return users_service.get_all_active_users(db)

@router.patch("/{employee_id}/approve", response_model=UserResponse)
def approve_user(employee_id: int, payload: ApproveUserRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_service.approve_user(employee_id, payload, db, current_user)

@router.patch("/{employee_id}/reject", response_model=UserResponse)
def reject_user(employee_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_service.reject_user(employee_id, db, current_user)

@router.delete("/{employee_id}")
def delete_user(employee_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_service.delete_user(employee_id, db, current_user)

@router.patch("/{employee_id}/team")
def update_employee_team(employee_id: int, payload: UpdateTeamRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_service.update_employee_team(employee_id, payload.team_id, db, current_user)