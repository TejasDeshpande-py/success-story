from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class StoryCreate(BaseModel):
    title: str
    designation: str = Field("", max_length=100)
    background: str
    challenge: str
    action_taken: str
    outcome: str
    ai_body: str
    extra: Optional[str] = None
    story_picture: Optional[str] = None
    story_for: Optional[int] = None
    story_for_tricon: Optional[str] = None
    is_team_story: bool = False
    team_id: Optional[int] = None


class EmployeeStoryUpdate(BaseModel):
    background: Optional[str] = None
    challenge: Optional[str] = None
    action_taken: Optional[str] = None
    outcome: Optional[str] = None


class HRStoryUpdate(BaseModel):
    background: Optional[str] = None
    challenge: Optional[str] = None
    action_taken: Optional[str] = None
    outcome: Optional[str] = None
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
    comment_count: int = 0

    class Config:
        from_attributes = True


class ReactRequest(BaseModel):
    emoji: str


class StoryResponse(BaseModel):
    story_id: int
    title: str
    designation: str
    background: str
    challenge: str
    action_taken: str
    outcome: str
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


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)

class CommentResponse(BaseModel):
    comment_id: int
    story_id: int
    employee_id: int
    body: str
    created_at: Optional[datetime]
    name: Optional[str] = None
    picture: Optional[str] = None

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
