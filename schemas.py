from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    picture: str
    type: str

    @field_validator("picture")
    def picture_must_be_valid_image(cls, v):
        if not any(v.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            raise ValueError("Picture must be a valid image URL (.jpg, .jpeg, .png, .webp)")
        return v

    @field_validator("email")
    def email_must_be_company(cls, v):
        if not v.endswith("@tricon.com"):
            raise ValueError("Email must be a @tricon.com address")
        return v

    @field_validator("type")
    def type_must_be_valid(cls, v):
        if v not in ["individual", "group"]:
            raise ValueError("Invalid type. Use 'individual' or 'group'")
        return v


class RegisterResponse(BaseModel):
    message: str
    employee_id: int
    name: str
    email: str
    type: str
    status: str


class ApproveUserRequest(BaseModel):
    role_id: int
    tricon_id: str
    team_id: Optional[int] = None

    @field_validator("role_id")
    def role_id_must_be_valid(cls, v):
        if v not in [0, 1]:
            raise ValueError("Invalid role. Use 0 for Employee or 1 for HR")
        return v

    @field_validator("tricon_id")
    def tricon_id_must_be_valid(cls, v):
        if not v.startswith("TRI"):
            raise ValueError("tricon_id must start with TRI e.g. TRI001")
        return v


class UserResponse(BaseModel):
    employee_id: int
    tricon_id: Optional[str]
    name: str
    email: str
    type: str
    role_id: Optional[int]
    team_id: Optional[int]
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    team_name: str


class TeamResponse(BaseModel):
    team_id: int
    team_name: str
    created_at: Optional[datetime]
    created_by: Optional[int]

    class Config:
        from_attributes = True


class StoryCreate(BaseModel):
    title: str
    designation: str
    body: str
    ai_body: str
    extra: Optional[str] = None
    story_for: int
    is_team_story: bool = False


class EmployeeStoryUpdate(BaseModel):
    body: str


class HRStoryUpdate(BaseModel):
    body: Optional[str] = None
    title: Optional[str] = None
    designation: Optional[str] = None
    ai_body: Optional[str] = None
    extra: Optional[str] = None


class StoryPublicResponse(BaseModel):
    story_id: int
    title: str
    designation: str
    content: str        
    extra: Optional[str]
    is_team_story: bool
    team_id: Optional[int]
    name: str
    picture: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class StoryResponse(BaseModel):
    story_id: int
    title: str
    designation: str
    body: str
    ai_body: str
    selected_body: Optional[bool]
    status: str
    extra: Optional[str]
    is_team_story: bool
    team_id: Optional[int]
    story_for: int
    created_by: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    updated_by: Optional[int]
    name: str
    picture: str

    class Config:
        from_attributes = True


class SelectBodyRequest(BaseModel):
    choice: Literal["original", "ai"]


class PublishResponse(BaseModel):
    message: str
    story_id: int


class RejectResponse(BaseModel):
    message: str
    story_id: int