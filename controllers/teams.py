from fastapi import HTTPException
from sqlalchemy.orm import Session
from model import Employee, Team
from schemas import TeamCreate


def create_team(payload: TeamCreate, db: Session, current_user: Employee):
    team = Team(
        team_name=payload.team_name,
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