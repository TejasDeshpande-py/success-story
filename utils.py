from model import SuccessStory


def paginate(page: int):
    limit = 10
    offset = (page - 1) * limit
    return limit, offset


def story_to_public_dict(s: SuccessStory):
    return {
        "story_id": s.story_id,
        "title": s.title,
        "designation": s.designation,
        "content": s.ai_body if s.selected_body == True else s.body,
        "extra": s.extra,
        "is_team_story": s.is_team_story,
        "team_id": s.team_id,
        "name": s.creator.name if s.creator else None,
        "picture": s.creator.picture if s.creator else None,
        "created_at": s.created_at,
    }


def story_to_dict(s: SuccessStory):
    return {
        "story_id": s.story_id,
        "title": s.title,
        "designation": s.designation,
        "body": s.body,
        "ai_body": s.ai_body,
        "selected_body": s.selected_body,
        "status": s.status,
        "extra": s.extra,
        "is_team_story": s.is_team_story,
        "team_id": s.team_id,
        "story_for": s.story_for,
        "created_by": s.created_by,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        "updated_by": s.updated_by,
        "name": s.creator.name if s.creator else None,
        "picture": s.creator.picture if s.creator else None,
    }