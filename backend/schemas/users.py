from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class UserResponse(BaseModel):
    employee_id: int
    tricon_id: Optional[str]
    name: str
    email: str
    role_id: Optional[int]
    team_id: Optional[int]
    status: str
    picture: Optional[str] = None
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

