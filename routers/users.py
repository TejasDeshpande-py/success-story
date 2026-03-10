from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from model import Employee
from schemas import UserResponse, ApproveUserRequest
from auth import require_hr_or_admin
from utils import paginate
import controllers.users as users_controller

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserResponse])
def get_all_users(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.get_active_users(page, db, paginate)


@router.get("/pending", response_model=List[UserResponse])
def get_pending_users(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.get_pending_users(page, db, paginate)


@router.patch("/{employee_id}/approve", response_model=UserResponse)
def approve_user(employee_id: int, payload: ApproveUserRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.approve_user(employee_id, payload, db, current_user)


@router.patch("/{employee_id}/reject", response_model=UserResponse)
def reject_user(employee_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return users_controller.reject_user(employee_id, db, current_user)