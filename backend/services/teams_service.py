import logging
import math
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.models.employee import Employee
from backend.models.team import Team
from backend.schemas.teams import TeamCreate
from backend.utils import paginate

logger = logging.getLogger(__name__)


def create_team(payload: TeamCreate, db: Session, current_user: Employee) -> Team:
    """Create new team."""
    team = Team(
        team_name=payload.team_name,
        team_picture=payload.team_picture,
        created_by=current_user.employee_id,
    )

    try:
        db.add(team)
        db.commit()
    except Exception as exc:
        logger.error("Failed to create team: %s", exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create team")

    db.refresh(team)
    return team


def get_all_teams(page: int, db: Session) -> dict:
    """Get teams paginated."""
    limit, offset = paginate(page)
    total = db.query(Team).count()
    teams = db.query(Team).offset(offset).limit(limit).all()
    return {
        "teams": teams,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }


def get_all_teams_list(db: Session) -> list:
    """Get all teams as list."""
    return db.query(Team).all()


def update_team(team_id: int, payload: dict, db: Session, current_user: Employee) -> Team:
    """Update existing team."""
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if "team_name" in payload and payload["team_name"]:
        team.team_name = payload["team_name"].strip()
    if "team_picture" in payload and payload["team_picture"]:
        team.team_picture = payload["team_picture"]
    
    try:
        db.commit()
        db.refresh(team)
    except Exception as exc:
        logger.error("Failed to update team %s: %s", team_id, exc)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update team")
    
    return team
