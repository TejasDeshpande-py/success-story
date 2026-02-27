from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class StoryCreate(BaseModel):
    title: str
    designation: str
    body: str
    ai_body: str
    selected_body: str
    extra: Optional[str] = None

class StoryUpdate(BaseModel):
    title: Optional[str] = None
    designation: Optional[str] = None
    body: Optional[str] = None
    ai_body: Optional[str] = None
    selected_body: Optional[str] = None
    extra: Optional[str] = None
    status: Optional[str] = None

class SelectBodyRequest(BaseModel):
    choice: str  