from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from backend.model import Employee, SuccessStory, StoryReaction
from backend.schemas import StoryCreate, EmployeeStoryUpdate, HRStoryUpdate, SelectBodyRequest, ReactRequest
from backend.utils import story_to_dict, story_to_public_dict

def get_my_stories(page: int, db: Session, paginate, current_user):
    import math
    limit, offset = paginate(page)
    total = db.query(SuccessStory).filter(
        SuccessStory.created_by == current_user.employee_id
    ).count()
    stories = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp)
    ).filter(
        SuccessStory.created_by == current_user.employee_id
    ).order_by(SuccessStory.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "stories": [story_to_dict(s) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }

def get_published_stories(page: int, db: Session, paginate, current_user_id: int = None):
    limit, offset = paginate(page)
    total = db.query(SuccessStory).filter(SuccessStory.status == "Posted").count()
    stories = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp),
        joinedload(SuccessStory.reactions).joinedload(StoryReaction.employee)
    ).filter(
        SuccessStory.status == "Posted"
    ).order_by(SuccessStory.created_at.desc()).offset(offset).limit(limit).all()
    import math
    return {
        "stories": [story_to_public_dict(s, current_user_id) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }

def get_story_detail(story_id: int, db: Session):
    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story_to_dict(story)

def get_published_story(story_id: int, db: Session, current_user_id: int = None):
    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp),
        joinedload(SuccessStory.reactions).joinedload(StoryReaction.employee)
    ).filter(
        SuccessStory.story_id == story_id,
        SuccessStory.status == "Posted"
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.view_count = (story.view_count or 0) + 1
    try:
        db.commit()
    except Exception:
        db.rollback()

    return story_to_public_dict(story, current_user_id)


def react_to_story(story_id: int, payload: ReactRequest, db: Session, current_user: Employee):
    ALLOWED = ["👍","❤️","😂","😮","😢","🙏","🎉","🏆","🔥","💪","🤝","🫂","👏","⭐","💯"]
    if payload.emoji not in ALLOWED:
        raise HTTPException(status_code=400, detail="Invalid emoji")

    existing = db.query(StoryReaction).filter(
        StoryReaction.story_id == story_id,
        StoryReaction.employee_id == current_user.employee_id
    ).first()

    if existing:
        if existing.emoji == payload.emoji:
            # same emoji → remove reaction
            db.delete(existing)
        else:
            # different emoji → switch reaction
            existing.emoji = payload.emoji
    else:
        # new reaction
        db.add(StoryReaction(
            story_id=story_id,
            employee_id=current_user.employee_id,
            emoji=payload.emoji
        ))

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save reaction")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp),
        joinedload(SuccessStory.reactions).joinedload(StoryReaction.employee)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_public_dict(story, current_user.employee_id)


def get_stories_by_status(status: str, page: int, db: Session, paginate):
    import math
    limit, offset = paginate(page)
    total = db.query(SuccessStory).filter(SuccessStory.status == status).count()
    stories = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp)
    ).filter(
        SuccessStory.status == status
    ).offset(offset).limit(limit).all()
    return {
        "stories": [story_to_dict(s) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }


def create_story(payload: StoryCreate, db: Session, current_user: Employee):
    # strip whitespace
    payload.title = payload.title.strip()
    payload.background = payload.background.strip()
    payload.challenge = payload.challenge.strip()
    payload.action_taken = payload.action_taken.strip()
    payload.outcome = payload.outcome.strip()
    payload.ai_body = payload.ai_body.strip()
    if payload.designation:
        payload.designation = payload.designation.strip()

    # whitespace-only content check
    if not payload.title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not payload.background.replace(' ', ''):
        raise HTTPException(status_code=400, detail="Background cannot be whitespace only")
    if not payload.challenge.replace(' ', ''):
        raise HTTPException(status_code=400, detail="Challenge cannot be whitespace only")
    if not payload.action_taken.replace(' ', ''):
        raise HTTPException(status_code=400, detail="Action taken cannot be whitespace only")
    if not payload.outcome.replace(' ', ''):
        raise HTTPException(status_code=400, detail="Outcome cannot be whitespace only")
    if not payload.ai_body.replace(' ', ''):
        raise HTTPException(status_code=400, detail="AI body cannot be whitespace only")

    # resolve story_for
    if payload.is_team_story:
        story_for_id = current_user.employee_id
    elif payload.story_for_tricon:
        emp = db.query(Employee).filter(Employee.tricon_id == payload.story_for_tricon).first()
        if not emp:
            raise HTTPException(status_code=404, detail="No employee found with that Tricon ID")
        if emp.status != "Active":
            raise HTTPException(status_code=400, detail="Cannot write a story for an inactive employee")
        if emp.employee_id == current_user.employee_id:
            raise HTTPException(status_code=400, detail="Use 'My Story' to write a story about yourself")
        story_for_id = emp.employee_id
    elif payload.story_for:
        emp = db.query(Employee).filter(Employee.employee_id == payload.story_for).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found for story_for")
        if emp.status != "Active":
            raise HTTPException(status_code=400, detail="Cannot write a story for an inactive employee")
        story_for_id = payload.story_for
    else:
        story_for_id = current_user.employee_id

    team_id = None
    if payload.is_team_story:
        if payload.team_id:
            from backend.model import Team
            team = db.query(Team).filter(Team.team_id == payload.team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="Selected team does not exist")
            team_id = payload.team_id
        elif current_user.team_id:
            team_id = current_user.team_id
        else:
            raise HTTPException(status_code=400, detail="Please select a team")

    # duplicate pending check — same title for same person
    duplicate = db.query(SuccessStory.story_id).filter(
        SuccessStory.created_by == current_user.employee_id,
        SuccessStory.story_for == story_for_id,
        SuccessStory.title == payload.title,
        SuccessStory.status == "Pending"
    ).scalar()
    if duplicate:
        raise HTTPException(status_code=400, detail="A pending story with this title for this person already exists.")

    story = SuccessStory(
        title=payload.title,
        designation=payload.designation,
        background=payload.background,
        challenge=payload.challenge,
        action_taken=payload.action_taken,
        outcome=payload.outcome,
        ai_body=payload.ai_body,
        selected_body=None,
        status="Pending",
        extra=payload.extra,
        story_picture=payload.story_picture,
        is_team_story=payload.is_team_story,
        team_id=team_id,
        story_for=story_for_id,
        created_by=current_user.employee_id,
    )

    try:
        db.add(story)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp)
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

    if payload.background is not None:
        story.background = payload.background
    if payload.challenge is not None:
        story.challenge = payload.challenge
    if payload.action_taken is not None:
        story.action_taken = payload.action_taken
    if payload.outcome is not None:
        story.outcome = payload.outcome
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def hr_edit_story(story_id: int, payload: HRStoryUpdate, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "title" in update_data and not update_data["title"].strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if "background" in update_data and not update_data["background"].strip():
        raise HTTPException(status_code=400, detail="Background cannot be empty")
    if "challenge" in update_data and not update_data["challenge"].strip():
        raise HTTPException(status_code=400, detail="Challenge cannot be empty")
    if "action_taken" in update_data and not update_data["action_taken"].strip():
        raise HTTPException(status_code=400, detail="Action taken cannot be empty")
    if "outcome" in update_data and not update_data["outcome"].strip():
        raise HTTPException(status_code=400, detail="Outcome cannot be empty")
    if "ai_body" in update_data and not update_data["ai_body"].strip():
        raise HTTPException(status_code=400, detail="AI body cannot be empty")
    if "designation" in update_data and not update_data["designation"].strip():
        raise HTTPException(status_code=400, detail="Designation cannot be empty")
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
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def select_body(story_id: int, payload: SelectBodyRequest, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status == "Posted":
        raise HTTPException(status_code=400, detail="Cannot change body of an already published story")
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
        joinedload(SuccessStory.creator), joinedload(SuccessStory.team), joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def publish_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status not in ["Pending", "Rejected"]:
        raise HTTPException(status_code=400, detail="Only pending or rejected stories can be published")

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

def delete_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        db.delete(story)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete story")
    return {"message": "Story deleted successfully", "story_id": story_id}


def unpublish_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != "Posted":
        raise HTTPException(status_code=400, detail="Only published stories can be unpublished")
    story.status = "Rejected"
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to unpublish story")
    return {"message": "Story unpublished successfully", "story_id": story_id}