from backend.model import SuccessStory


def paginate(page: int):
    limit = 10
    offset = (page - 1) * limit
    return limit, offset


def story_to_public_dict(s: SuccessStory, current_user_id: int = None):
    
    # group reactions by emoji
    reaction_map = {}
    for r in (s.reactions or []):
        if r.emoji not in reaction_map:
            reaction_map[r.emoji] = {"emoji": r.emoji, "count": 0, "names": []}
        reaction_map[r.emoji]["count"] += 1
        reaction_map[r.emoji]["names"].append(r.employee.name if r.employee else "Unknown")

    my_reaction = None
    if current_user_id:
        for r in (s.reactions or []):
            if r.employee_id == current_user_id:
                my_reaction = r.emoji
                break

    return {
        "story_id": s.story_id,
        "title": s.title,
        "designation": s.designation,
        "content": s.ai_body if s.selected_body == True else s.body,
        "extra": s.extra,
        "is_team_story": s.is_team_story,
        "team_id": s.team_id,
        "name": s.team.team_name if s.is_team_story and s.team else (s.story_for_emp.name if s.story_for_emp else None),
        "picture": s.team.team_picture if s.is_team_story and s.team else (s.story_for_emp.picture if s.story_for_emp else None),
        "story_picture": s.story_picture,
        "view_count": s.view_count or 0,
        "created_by_name": s.creator.name if s.creator else None,
        "created_at": s.created_at,
        "reactions": list(reaction_map.values()),
        "my_reaction": my_reaction,
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
        "name": s.team.team_name if s.is_team_story and s.team else (s.story_for_emp.name if s.story_for_emp else None),
        "picture": s.team.team_picture if s.is_team_story and s.team else (s.story_for_emp.picture if s.story_for_emp else None),
    }