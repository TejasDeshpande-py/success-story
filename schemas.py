from typing import Optional
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

    @field_validator("name")
    def name_must_not_be_empty(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v.strip()

    @field_validator("password")
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("picture")
    def picture_must_be_jpg(cls, v):
        if not v.endswith(".jpg"):
            raise ValueError("Picture must be a .jpg URL")
        return v

    @field_validator("email")
    def email_must_be_company(cls, v):
        if not v.endswith("@company.com"):
            raise ValueError("Email must be a @company.com address")
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
    team_id: int

    @field_validator("role_id")
    def role_id_must_be_valid(cls, v):
        if v not in [0, 1]:
            raise ValueError("Invalid role. Use 0 for Employee or 1 for HR")
        return v

    @field_validator("team_id")
    def team_id_must_be_valid(cls, v):
        if v <= 0:
            raise ValueError("team_id must be a positive number")
        return v
class UserResponse(BaseModel):
    employee_id: int
    name: str
    email: str
    type: str
    role_id: Optional[int]
    team_id: Optional[int]
    status: str

    class Config:
        from_attributes = True

class StoryCreate(BaseModel):
    title: str
    designation: str
    body: str
    ai_body: str
    extra: Optional[str] = None

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
    selected_body: bool        # always True/False for published stories
    extra: Optional[str]
    name: str
    picture: str

    class Config:
        from_attributes = True

class StoryResponse(BaseModel):
    story_id: int
    title: str
    designation: str
    body: str
    ai_body: str
    selected_body: Optional[bool]   # can be None for pending stories
    status: str
    extra: Optional[str]
    name: str
    picture: str
    created_by: int

    class Config:
        from_attributes = True

class PublishResponse(BaseModel):
    message: str
    story_id: int

class RejectResponse(BaseModel):
    message: str
    story_id: int

class SelectBodyRequest(BaseModel):
    choice: str

    @field_validator("choice")
    def choice_must_be_valid(cls, v):
        if v not in ["original", "ai"]:
            raise ValueError("Choice must be 'original' or 'ai'")
        return v