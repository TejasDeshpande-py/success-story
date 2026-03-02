from typing import Optional
from pydantic import BaseModel

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
    role_id: int

class RegisterResponse(BaseModel):
    message: str
    employee_id: int
    email: str
    role_id: int

class StoryCreate(BaseModel):
    title: str
    designation: str
    body: str
    ai_body: str
    selected_body: Optional[str] = None
    extra: Optional[str] = None

class StoryPublicResponse(BaseModel):
    story_id: int
    title: str
    designation: Optional[str]
    body: str
    selected_body: Optional[str]
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