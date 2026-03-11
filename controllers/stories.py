from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from model import Employee, SuccessStory
from schemas import StoryCreate, EmployeeStoryUpdate, HRStoryUpdate, SelectBodyRequest
from utils import story_to_dict, story_to_public_dict

def get_my_stories(page: int, db: Session, paginate, current_user):
    limit, offset = paginate(page)
    return db.query(SuccessStory).filter(
        SuccessStory.created_by == current_user.employee_id
    ).offset(offset).limit(limit).all()

def get_story_detail(story_id: int, db: Session):
    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story_to_dict(story)

def get_published_stories(page: int, db: Session, paginate):
    limit, offset = paginate(page)
    stories = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(
        SuccessStory.status == "Posted"
    ).offset(offset).limit(limit).all()
    return [story_to_public_dict(s) for s in stories]

def get_story_detail(story_id: int, db: Session):
    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story_to_dict(story)

def get_published_story(story_id: int, db: Session):
    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(
        SuccessStory.story_id == story_id,
        SuccessStory.status == "Posted"
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return story_to_public_dict(story)


def get_stories_by_status(status: str, page: int, db: Session, paginate):
    limit, offset = paginate(page)
    stories = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(
        SuccessStory.status == status
    ).offset(offset).limit(limit).all()
    return [story_to_dict(s) for s in stories]


def create_story(payload: StoryCreate, db: Session, current_user: Employee):
    exists = db.query(Employee.employee_id).filter(
        Employee.employee_id == payload.story_for
    ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Employee not found for story_for")

    team_id = None
    if payload.is_team_story:
        if current_user.team_id is None:
            raise HTTPException(status_code=400, detail="You are not assigned to a team")
        team_id = current_user.team_id

    story = SuccessStory(
        title=payload.title,
        designation=payload.designation,
        body=payload.body,
        ai_body=payload.ai_body,
        selected_body=None,
        status="Pending",
        extra=payload.extra,
        is_team_story=payload.is_team_story,
        team_id=team_id,
        story_for=payload.story_for,
        created_by=current_user.employee_id,
    )

    try:
        db.add(story)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(SuccessStory.story_id == story.story_id).first()

    return story_to_dict(story)


def edit_story(story_id: int, payload: EmployeeStoryUpdate, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.created_by != current_user.employee_id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this story")

    if story.status not in ["Pending", "Rejected"]:
        raise HTTPException(status_code=400, detail="You can only edit Pending or Rejected stories")

    story.body = payload.body
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def hr_edit_story(story_id: int, payload: HRStoryUpdate, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)

    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def select_body(story_id: int, payload: SelectBodyRequest, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can have body selected")

    story.selected_body = payload.choice == "ai"

    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to select body")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def publish_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can be published")

    if story.selected_body is None:
        raise HTTPException(status_code=400, detail="A body must be selected before publishing")

    story.status = "Posted"
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to publish story")

    return {"message": "Story published successfully", "story_id": story.story_id}


def reject_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can be rejected")

    story.status = "Rejected"
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reject story")

    return {"message": "Story rejected successfully", "story_id": story.story_id}