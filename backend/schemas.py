from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, field_validator, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    name: str = Field(..., max_length=50)
    email: str
    password: str
    picture: str
    tricon_id: str

    @field_validator("picture")
    def picture_must_be_valid_image(cls, v):
        if not any(v.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            raise ValueError("Picture must be a valid image URL (.jpg, .jpeg, .png, .webp)")
        return v

    @field_validator("email")
    def email_must_be_company(cls, v):
        if not v.endswith("@triconinfotech.com"):
            raise ValueError("Email must be a @triconinfotech.com address")
        return v

    @field_validator("tricon_id")
    def tricon_id_must_be_valid(cls, v):
        if not v.startswith("TRI"):
            raise ValueError("tricon_id must start with TRI e.g. TRI001")
        return v


class RegisterResponse(BaseModel):
    message: str
    employee_id: int
    name: str
    email: str
    status: str


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


class StoryCreate(BaseModel):
    title: str
    designation: str = Field("", max_length=100)
    body: str
    ai_body: str
    extra: Optional[str] = None
    story_picture: Optional[str] = None
    story_for: Optional[int] = None
    story_for_tricon: Optional[str] = None
    is_team_story: bool = False
    team_id: Optional[int] = None


class EmployeeStoryUpdate(BaseModel):
    body: str


class HRStoryUpdate(BaseModel):
    body: Optional[str] = None
    title: Optional[str] = None
    designation: Optional[str] = None
    ai_body: Optional[str] = None
    extra: Optional[str] = Field(None, max_length=100)


class ReactionSummary(BaseModel):
    emoji: str
    count: int
    names: list[str]

class StoryPublicResponse(BaseModel):
    story_id: int
    title: str
    designation: str
    content: str        
    extra: Optional[str]
    is_team_story: bool
    team_id: Optional[int]
    name: Optional[str]
    picture: Optional[str]
    story_picture: Optional[str] = None
    view_count: int = 0
    created_by_name: Optional[str] = None
    created_at: Optional[datetime]
    reactions: list[ReactionSummary] = []
    my_reaction: Optional[str] = None

    class Config:
        from_attributes = True


class ReactRequest(BaseModel):
    emoji: str


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
    name: Optional[str]
    picture: Optional[str]
    story_picture: Optional[str] = None

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