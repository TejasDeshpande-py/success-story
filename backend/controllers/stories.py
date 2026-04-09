import math
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from backend.model import Employee, SuccessStory, StoryReaction, Team
from backend.schemas import StoryCreate, EmployeeStoryUpdate, HRStoryUpdate, SelectBodyRequest, ReactRequest
from backend.utils import story_to_dict, story_to_public_dict, paginate

logger = logging.getLogger(__name__)


def get_my_stories(page: int, db: Session, current_user):
    limit, offset = paginate(page)
    total = db.query(SuccessStory).filter(
        SuccessStory.created_by == current_user.employee_id
    ).count()
    stories = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp)
    ).filter(
        SuccessStory.created_by == current_user.employee_id
    ).order_by(SuccessStory.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "stories": [story_to_dict(s) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


def get_published_stories(page: int, db: Session, current_user_id: int = None, search: str = None):
    limit, offset = paginate(page)
    query = db.query(SuccessStory).filter(SuccessStory.status == "Posted")
    if search:
        term = f"%{search.strip()}%"
        query = query.join(SuccessStory.story_for_emp).filter(
            Employee.name.ilike(term)
        )
    total = query.count()
    stories = query.options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp),
        joinedload(SuccessStory.reactions).joinedload(StoryReaction.employee)
    ).order_by(SuccessStory.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "stories": [story_to_public_dict(s, current_user_id) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }

def get_story_detail(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if current_user.role_id not in [1, 2] and story.created_by != current_user.employee_id:
        raise HTTPException(status_code=403, detail="Not allowed to view this story")

    return story_to_dict(story)


def get_published_story(story_id: int, db: Session, current_user_id: int = None):
    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp),
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
    except Exception as exc:
        # FIX: bare except swallowed error silently — now logged
        logger.warning("Failed to increment view count for story %s: %s", story_id, exc)
        db.rollback()

    return story_to_public_dict(story, current_user_id)


def react_to_story(story_id: int, payload: ReactRequest, db: Session, current_user: Employee):
    ALLOWED = ["👍","❤️","😂","😮","😢","🙏","🎉","🏆","🔥","💪","🤝","🫂","👏","⭐","💯"]
    if payload.emoji not in ALLOWED:
        raise HTTPException(status_code=400, detail="Invalid emoji")

    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    existing = db.query(StoryReaction).filter(
        StoryReaction.story_id == story_id,
        StoryReaction.employee_id == current_user.employee_id
    ).first()

    if existing:
        if existing.emoji == payload.emoji:
            db.delete(existing)
        else:
            existing.emoji = payload.emoji
    else:
        db.add(StoryReaction(
            story_id=story_id,
            employee_id=current_user.employee_id,
            emoji=payload.emoji
        ))

    try:
        db.commit()
    except Exception as exc:
        # FIX: bare except swallowed error silently — now logged
        logger.error("Failed to save reaction for story %s by user %s: %s", story_id, current_user.employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save reaction")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp),
        joinedload(SuccessStory.reactions).joinedload(StoryReaction.employee)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_public_dict(story, current_user.employee_id)


def get_stories_by_status(status: str, page: int, db: Session):
    limit, offset = paginate(page)
    total = db.query(SuccessStory).filter(SuccessStory.status == status).count()
    # FIX: was missing .offset(offset).limit(limit) — same pagination bug as get_published_stories
    stories = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp)
    ).filter(
        SuccessStory.status == status
    ).order_by(SuccessStory.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "stories": [story_to_dict(s) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


def create_story(payload: StoryCreate, db: Session, current_user: Employee):
    payload.title = payload.title.strip()
    payload.background = payload.background.strip()
    payload.challenge = payload.challenge.strip()
    payload.action_taken = payload.action_taken.strip()
    payload.outcome = payload.outcome.strip()
    payload.ai_body = payload.ai_body.strip()
    if payload.designation:
        payload.designation = payload.designation.strip()

    # FIX: was `not payload.x.replace(' ', '')` — only caught spaces, missed \n \t
    # .strip() already called above, plain truthiness check is correct and sufficient
    if not payload.title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not payload.background:
        raise HTTPException(status_code=400, detail="Background cannot be empty")
    if not payload.challenge:
        raise HTTPException(status_code=400, detail="Challenge cannot be empty")
    if not payload.action_taken:
        raise HTTPException(status_code=400, detail="Action taken cannot be empty")
    if not payload.outcome:
        raise HTTPException(status_code=400, detail="Outcome cannot be empty")
    if not payload.ai_body:
        raise HTTPException(status_code=400, detail="AI body cannot be empty")

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
            # FIX: `from backend.model import Team` was inside function body — moved to top of file
            team = db.query(Team).filter(Team.team_id == payload.team_id).first()
            if not team:
                raise HTTPException(status_code=404, detail="Selected team does not exist")
            team_id = payload.team_id
        elif current_user.team_id:
            team_id = current_user.team_id
        else:
            raise HTTPException(status_code=400, detail="Please select a team")

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
    except Exception as exc:
        # FIX: bare except swallowed error silently — now logged
        logger.error("Failed to create story by user %s: %s", current_user.employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story.story_id).first()

    return story_to_dict(story)


def edit_story(story_id: int, payload: EmployeeStoryUpdate, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.created_by != current_user.employee_id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this story")
    if story.status not in ["Pending", "Rejected"]:
        raise HTTPException(status_code=400, detail="You can only edit Pending or Rejected stories")

    # FIX: only background had the empty-string guard — challenge/action_taken/outcome did not
    # All four fields now consistently validated before update
    if payload.background is not None:
        if not payload.background.strip():
            raise HTTPException(status_code=400, detail="Background cannot be empty")
        story.background = payload.background
    if payload.challenge is not None:
        if not payload.challenge.strip():
            raise HTTPException(status_code=400, detail="Challenge cannot be empty")
        story.challenge = payload.challenge
    if payload.action_taken is not None:
        if not payload.action_taken.strip():
            raise HTTPException(status_code=400, detail="Action taken cannot be empty")
        story.action_taken = payload.action_taken
    if payload.outcome is not None:
        if not payload.outcome.strip():
            raise HTTPException(status_code=400, detail="Outcome cannot be empty")
        story.outcome = payload.outcome

    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        # FIX: bare except swallowed error silently — now logged
        logger.error("Failed to edit story %s by user %s: %s", story_id, current_user.employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def hr_edit_story(story_id: int, payload: HRStoryUpdate, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()

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
    except Exception as exc:
        # FIX: bare except swallowed error silently — now logged
        logger.error("Failed to HR-edit story %s by user %s: %s", story_id, current_user.employee_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update story")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def select_body(story_id: int, payload: SelectBodyRequest, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status == "Posted":
        raise HTTPException(status_code=400, detail="Cannot change body of an already published story")
    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can have body selected")

    # FIX: was `payload.choice not in ["ai", "manual"]` — schema uses Literal["original", "ai"]
    # "original" would always fail this check and get rejected as invalid
    # Removed — Literal on the schema already enforces valid values at the boundary
    story.selected_body = payload.choice == "ai"
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to select body for story %s: %s", story_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to select body")

    story = db.query(SuccessStory).options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.team),
        joinedload(SuccessStory.story_for_emp)
    ).filter(SuccessStory.story_id == story_id).first()

    return story_to_dict(story)


def publish_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status not in ["Pending", "Rejected"]:
        raise HTTPException(status_code=400, detail="Only pending or rejected stories can be published")

    # FIX: was `story.selected_body is None or story.selected_body not in [True, False]`
    # selected_body is a boolean column — only possible values are True, False, None
    # `not in [True, False]` is exactly equivalent to `is None` — redundant condition removed
    if story.selected_body is None:
        raise HTTPException(status_code=400, detail="A body must be selected before publishing")

    story.status = "Posted"
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to publish story %s: %s", story_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to publish story")

    return {"message": "Story published successfully", "story_id": story.story_id}


def reject_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can be rejected")

    story.status = "Rejected"
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to reject story %s: %s", story_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to reject story")

    return {"message": "Story rejected successfully", "story_id": story.story_id}


def delete_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.created_by != current_user.employee_id and current_user.role_id not in [1, 2]:
        raise HTTPException(status_code=403, detail="Not allowed to delete this story")
    try:
        db.delete(story)
        db.commit()
    except Exception as exc:
        logger.error("Failed to delete story %s: %s", story_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete story")
    return {"message": "Story deleted successfully", "story_id": story_id}


def unpublish_story(story_id: int, db: Session, current_user: Employee):
    story = db.query(SuccessStory).filter(SuccessStory.story_id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != "Posted":
        raise HTTPException(status_code=400, detail="Only published stories can be unpublished")
    story.status = "Pending"
    story.updated_by = current_user.employee_id
    story.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(story)
    except Exception as exc:
        logger.error("Failed to unpublish story %s: %s", story_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to unpublish story")
    return {"message": "Story unpublished successfully", "story_id": story_id}

def get_comments(story_id: int, db: Session):
    from backend.model import StoryComment
    comments = db.query(StoryComment).options(
        joinedload(StoryComment.employee)
    ).filter(StoryComment.story_id == story_id).order_by(StoryComment.created_at.asc()).all()
    return [
        {
            "comment_id": c.comment_id,
            "story_id": c.story_id,
            "employee_id": c.employee_id,
            "body": c.body,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "name": c.employee.name if c.employee else None,
            "picture": c.employee.picture if c.employee else None,
        }
        for c in comments
    ]


def add_comment(story_id: int, body: str, db: Session, current_user: Employee):
    from backend.model import StoryComment
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id,
        SuccessStory.status == "Posted"
    ).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if not body.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    comment = StoryComment(
        story_id=story_id,
        employee_id=current_user.employee_id,
        body=body.strip()
    )
    db.add(comment)
    try:
        db.commit()
        db.refresh(comment)
    except Exception as exc:
        logger.error("Failed to add comment: %s", exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add comment")
    comment = db.query(StoryComment).options(
        joinedload(StoryComment.employee)
    ).filter(StoryComment.comment_id == comment.comment_id).first()
    return {
        "comment_id": comment.comment_id,
        "story_id": comment.story_id,
        "employee_id": comment.employee_id,
        "body": comment.body,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "name": comment.employee.name if comment.employee else None,
        "picture": comment.employee.picture if comment.employee else None,
    }


def delete_comment(story_id: int, comment_id: int, db: Session, current_user: Employee):
    from backend.model import StoryComment
    comment = db.query(StoryComment).filter(
        StoryComment.comment_id == comment_id,
        StoryComment.story_id == story_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.employee_id != current_user.employee_id and current_user.role_id not in [1, 2]:
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")
    try:
        db.delete(comment)
        db.commit()
    except Exception as exc:
        logger.error("Failed to delete comment %s: %s", comment_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete comment")
    return {"message": "Comment deleted", "comment_id": comment_id}