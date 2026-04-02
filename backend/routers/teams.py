from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.model import Employee
from backend.schemas import TeamCreate, TeamResponse
from backend.auth import require_hr_or_admin, get_current_user
from backend.utils import paginate
import backend.controllers.teams as teams_controller

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("/", response_model=TeamResponse, status_code=201)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return teams_controller.create_team(payload, db, current_user)


@router.get("/", response_model=List[TeamResponse])
def get_teams(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin)
):
    return teams_controller.get_all_teams(page, db, paginate)

@router.get("/all", response_model=List[TeamResponse])
def get_all_teams_list(db: Session = Depends(get_db), current_user: Employee = Depends(get_current_user)):
    return teams_controller.get_all_teams_list(db)

@router.patch("/{team_id}")
def update_team(team_id: int, payload: dict, db: Session = Depends(get_db), current_user: Employee = Depends(require_hr_or_admin)):
    return teams_controller.update_team(team_id, payload, db, current_user)