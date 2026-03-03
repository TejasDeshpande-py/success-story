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
    role_id: int        # 0 = Employee, 1 = HR
    type: str           # "individual" or "group"
    team_id: int

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

    @field_validator("role_id")
    def role_id_must_be_valid(cls, v):
        if v not in [0, 1]:
            raise ValueError("Invalid role. Use 0 for Employee or 1 for HR")
        return v

    @field_validator("type")
    def type_must_be_valid(cls, v):
        if v not in ["individual", "group"]:
            raise ValueError("Invalid type. Use 'individual' or 'group'")
        return v

    @field_validator("team_id")
    def team_id_must_be_positive(cls, v):
        if v < 1:
            raise ValueError("team_id must be a positive number")
        return v

class RegisterResponse(BaseModel):
    message: str
    employee_id: int
    name: str
    email: str
    role_id: int
    type: str
    team_id: int

class StoryCreate(BaseModel):
    title: str
    designation: Optional[str] = None
    body: str
    ai_body: str
    extra: Optional[str] = None

class StoryPublicResponse(BaseModel):
    story_id: int
    title: str
    designation: str
    selected_body: str
    status: str
    extra: Optional[str]
    created_by: int

    class Config:
        from_attributes = True

class StoryResponse(BaseModel):
    story_id: int
    title: str
    designation: Optional[str]
    body: str
    ai_body: str
    selected_body: Optional[str]
    status: str
    extra: Optional[str]
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