from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class TeamCreate(BaseModel):
    team_name: str
    team_picture: str

class TeamResponse(BaseModel):
    team_id: int
    team_name: str
    team_picture: Optional[str]
    created_at: Optional[datetime]
    created_by: Optional[int]

    class Config:
        from_attributes = True
