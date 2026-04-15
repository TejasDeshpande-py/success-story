from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


class ApproveUserRequest(BaseModel):
    role_id: int
    team_id: Optional[int] = None

    @field_validator("role_id")
    def role_id_must_be_valid(cls, v):
        if v not in [0, 1]:
            raise ValueError("Invalid role. Use 0 for Employee or 1 for HR")
        return v


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