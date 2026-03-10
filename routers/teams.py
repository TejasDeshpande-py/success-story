from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from model import Employee
from schemas import TeamCreate, TeamResponse
from auth import require_hr_or_admin
from utils import paginate
import controllers.teams as teams_controller

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