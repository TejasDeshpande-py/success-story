from fastapi import HTTPException
from sqlalchemy.orm import Session
from model import Employee, Team
from schemas import TeamCreate


def create_team(payload: TeamCreate, db: Session, current_user: Employee):
    team = Team(
        team_name=payload.team_name,
        team_picture=payload.team_picture,
        created_by=current_user.employee_id,
    )

    try:
        db.add(team)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create team")

    db.refresh(team)
    return team


def get_all_teams(page: int, db: Session, paginate):
    limit, offset = paginate(page)
    return db.query(Team).offset(offset).limit(limit).all()

def get_all_teams_list(db: Session):
    return db.query(Team).all()


def update_team(team_id: int, payload: dict, db: Session, current_user: Employee):
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
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update team")
    return team