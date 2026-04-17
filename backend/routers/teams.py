from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.db import get_db
from backend.models.employee import Employee
from backend.schemas.teams import TeamCreate, TeamResponse
from backend.auth.dependencies import require_hr_or_admin, get_current_user
from backend.utils import paginate
from backend.services import teams_service

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("/", response_model=TeamResponse, status_code=201)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return teams_service.create_team(payload, db, current_user)


@router.get("/", response_model=List[TeamResponse])
def get_teams(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return teams_service.get_all_teams(page, db)


@router.get("/all", response_model=List[TeamResponse])
def get_all_teams_list(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return teams_service.get_all_teams_list(db)


@router.patch("/{team_id}")
def update_team(team_id: int, payload: dict, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return teams_service.update_team(team_id, payload, db, current_user)

