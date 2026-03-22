from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from model import Employee
from schemas import (
    StoryCreate, StoryResponse, StoryPublicResponse,
    PublishResponse, RejectResponse, SelectBodyRequest,
    EmployeeStoryUpdate, HRStoryUpdate
)
from auth import get_current_user, require_hr_or_admin
import controllers.stories as stories_controller
from utils import paginate

router = APIRouter(prefix="/stories", tags=["Stories"])

@router.get("/mine")
def get_my_stories(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return stories_controller.get_my_stories(page, db, paginate, current_user)

@router.get("/pending", response_model=List[StoryResponse])
def get_pending_stories(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.get_stories_by_status("Pending", page, db, paginate)

@router.get("/detail/{story_id}", response_model=StoryResponse)
def get_story_detail(story_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.get_story_detail(story_id, db)

@router.get("/rejected", response_model=List[StoryResponse])
def get_rejected_stories(page: int = 1, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.get_stories_by_status("Rejected", page, db, paginate)


@router.post("/create", response_model=StoryResponse, status_code=201)
def create_story(payload: StoryCreate, db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return stories_controller.create_story(payload, db, current_user)

@router.get("/detail/{story_id}", response_model=StoryResponse)
def get_story_detail(story_id: int, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return stories_controller.get_story_detail(story_id, db)

@router.get("/")
def get_stories(page: int = 1, db: Session = Depends(get_db)):
    return stories_controller.get_published_stories(page, db, paginate)
@router.get("/{story_id}", response_model=StoryPublicResponse)
def get_story(story_id: int, db: Session = Depends(get_db)):
    return stories_controller.get_published_story(story_id, db)


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