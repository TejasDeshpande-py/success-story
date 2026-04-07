from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.model import Employee
from backend.schemas import (
    StoryCreate, StoryResponse, StoryPublicResponse,
    PublishResponse, RejectResponse, SelectBodyRequest,
    EmployeeStoryUpdate, HRStoryUpdate, ReactRequest
)
from backend.auth import get_current_user, require_hr_or_admin
from typing import Optional
from fastapi import Request
from backend.security import decode_token
from jose import JWTError
import backend.controllers.stories as stories_controller

router = APIRouter(prefix="/stories", tags=["Stories"])

def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[Employee]:
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return None
        payload = decode_token(token)
        email = payload.get("sub")
        if not email:
            return None
        return db.query(Employee).filter(Employee.email == email).first()
    except (JWTError, Exception):
        return None

@router.get("/mine")
def get_my_stories(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return stories_controller.get_my_stories(page, db, current_user)

@router.get("/pending")
def get_pending_stories(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.get_stories_by_status("Pending", page, db)

@router.get("/detail/{story_id}", response_model=StoryResponse)
def get_story_detail(story_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return stories_controller.get_story_detail(story_id, db, current_user)

@router.get("/rejected")
def get_rejected_stories(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.get_stories_by_status("Rejected", page, db)


@router.post("/create", response_model=StoryResponse, status_code=201)
def create_story(payload: StoryCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return stories_controller.create_story(payload, db, current_user)



@router.get("/")
def get_stories(page: int = 1, db: Session = Depends(get_db), current_user: Optional[Employee] = Depends(get_optional_user)):
    uid = current_user.employee_id if current_user else None
    return stories_controller.get_published_stories(page, db, uid)

@router.get("/{story_id}", response_model=StoryPublicResponse)
def get_story(story_id: int, db: Session = Depends(get_db), current_user: Optional[Employee] = Depends(get_optional_user)):
    uid = current_user.employee_id if current_user else None
    return stories_controller.get_published_story(story_id, db, uid)

@router.post("/{story_id}/react")
def react_to_story(story_id: int, payload: ReactRequest, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return stories_controller.react_to_story(story_id, payload, db, current_user)


@router.patch("/{story_id}/edit", response_model=StoryResponse)
def hr_edit_story(story_id: int, payload: HRStoryUpdate, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.hr_edit_story(story_id, payload, db, current_user)


@router.patch("/{story_id}/select-body", response_model=StoryResponse)
def select_body(story_id: int, payload: SelectBodyRequest, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.select_body(story_id, payload, db, current_user)


@router.patch("/{story_id}/publish", response_model=PublishResponse)
def publish_story(story_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.publish_story(story_id, db, current_user)


@router.patch("/{story_id}/reject", response_model=RejectResponse)
def reject_story(story_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.reject_story(story_id, db, current_user)


@router.patch("/{story_id}", response_model=StoryResponse)
def edit_story(story_id: int, payload: EmployeeStoryUpdate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return stories_controller.edit_story(story_id, payload, db, current_user)

@router.delete("/{story_id}")
def delete_story(story_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.delete_story(story_id, db, current_user)

@router.patch("/{story_id}/unpublish")
def unpublish_story(story_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.unpublish_story(story_id, db, current_user)