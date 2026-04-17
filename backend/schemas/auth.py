from typing import Optional
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

