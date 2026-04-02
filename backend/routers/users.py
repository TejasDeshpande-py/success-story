from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from model import Employee
from schemas import UserResponse, ApproveUserRequest
from utils import paginate
import controllers.users as users_controller
from auth import require_hr_or_admin, get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
def get_all_users(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.get_active_users(page, db, paginate)

@router.get("/me", response_model=UserResponse)
def get_me(db=Depends(get_db), current_user=Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_me(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return users_controller.update_me(payload, db, current_user)

@router.get("/pending")
def get_pending_users(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.get_pending_users(page, db, paginate)

@router.get("/all", response_model=List[UserResponse])
def get_all_users_list(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return users_controller.get_all_active_users(db)

@router.patch("/{employee_id}/approve", response_model=UserResponse)
def approve_user(employee_id: int, payload: ApproveUserRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.approve_user(employee_id, payload, db, current_user)


@router.patch("/{employee_id}/reject", response_model=UserResponse)
def reject_user(employee_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.reject_user(employee_id, db, current_user)

@router.delete("/{employee_id}")
def delete_user(employee_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.delete_user(employee_id, db, current_user)

@router.patch("/{employee_id}/team")
def update_employee_team(employee_id: int, payload: dict, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.update_employee_team(employee_id, payload, db, current_user)