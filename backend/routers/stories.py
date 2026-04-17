from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.employee import Employee
from backend.schemas.stories import (
    StoryCreate, StoryResponse, StoryPublicResponse,
    PublishResponse, RejectResponse, SelectBodyRequest,
    EmployeeStoryUpdate, HRStoryUpdate, ReactRequest,
    CommentCreate, CommentResponse
)
from backend.auth.dependencies import get_current_user, get_optional_user, require_hr_or_admin
from backend.services import stories_service
from backend.middleware.limiter import limiter
from typing import Optional

router = APIRouter(prefix="/stories", tags=["Stories"])


@router.get("/mine")
def get_my_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.get_my_stories(page, db, current_user)


@router.get("/pending")
def get_pending_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.get_stories_by_status("Pending", page, db)


@router.get("/detail/{story_id}", response_model=StoryResponse)
def get_story_detail(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.get_story_detail(story_id, db, current_user)


@router.get("/rejected")
def get_rejected_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.get_stories_by_status("Rejected", page, db)


@router.post("/create", response_model=StoryResponse, status_code=201)
@limiter.limit("10/minute")
def create_story(
    request: Request,
    payload: StoryCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.create_story(payload, db, current_user)


@router.get("/")
@limiter.limit("60/minute")
def get_stories(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    sort_by: Optional[str] = "recent",
    db: Session = Depends(get_db),
    current_user: Optional[Employee] = Depends(get_optional_user)
):
    uid = current_user.employee_id if current_user else None
    return stories_service.get_published_stories(page, db, uid, search, sort_by)


@router.get("/{story_id}", response_model=StoryPublicResponse)
def get_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[Employee] = Depends(get_optional_user)
):
    uid = current_user.employee_id if current_user else None
    return stories_service.get_published_story(story_id, db, uid)


@router.post("/{story_id}/react")
@limiter.limit("30/minute")
def react_to_story(
    request: Request,
    story_id: int,
    payload: ReactRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.react_to_story(story_id, payload, db, current_user)


@router.patch("/{story_id}/edit", response_model=StoryResponse)
def hr_edit_story(
    story_id: int,
    payload: HRStoryUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.hr_edit_story(story_id, payload, db, current_user)


@router.patch("/{story_id}/select-body", response_model=StoryResponse)
def select_body(
    story_id: int,
    payload: SelectBodyRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.select_body(story_id, payload, db, current_user)


@router.patch("/{story_id}/publish", response_model=PublishResponse)
def publish_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.publish_story(story_id, db, current_user)


@router.patch("/{story_id}/reject", response_model=RejectResponse)
def reject_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.reject_story(story_id, db, current_user)


@router.patch("/{story_id}", response_model=StoryResponse)
def edit_story(
    story_id: int,
    payload: EmployeeStoryUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.edit_story(story_id, payload, db, current_user)


@router.delete("/{story_id}")
def delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.delete_story(story_id, db, current_user)


@router.patch("/{story_id}/unpublish")
def unpublish_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return stories_service.unpublish_story(story_id, db, current_user)


# ── Comments ──────────────────────────────────────────────────────────────────
# FIX: was completely unauthenticated before — anyone on internet could read comments

@router.get("/{story_id}/comments")
def get_comments(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.get_comments(story_id, db, current_user)


@router.post("/{story_id}/comments")
@limiter.limit("20/minute")
def add_comment(
    request: Request,
    story_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.add_comment(story_id, payload.body, db, current_user)


@router.delete("/{story_id}/comments/{comment_id}")
@limiter.limit("20/minute")
def delete_comment(
    request: Request,
    story_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    return stories_service.delete_comment(story_id, comment_id, db, current_user)