from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db import Base


class SuccessStory(Base):
    __tablename__ = "success_stories"

    story_id      = Column(Integer, primary_key=True, index=True)
    title         = Column(String(200), nullable=False)
    designation   = Column(String(120), nullable=False)
    background    = Column(Text, nullable=False)
    challenge     = Column(Text, nullable=False)
    action_taken  = Column(Text, nullable=False)
    outcome       = Column(Text, nullable=False)
    ai_body       = Column(Text, nullable=False)
    selected_body = Column(Boolean, nullable=True, default=None)
    status        = Column(Enum("Pending", "Posted", "Rejected"), nullable=False, default="Pending")
    extra         = Column(String(500), nullable=True)
    story_picture = Column(String(500), nullable=True)
    view_count    = Column(Integer, nullable=False, default=0)
    is_team_story = Column(Boolean, nullable=False, default=False)
    team_id       = Column(Integer, ForeignKey("teams.team_id"), nullable=True, default=None)
    story_for     = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    created_by    = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, onupdate=func.now(), nullable=True)
    updated_by    = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)

    creator       = relationship("Employee", back_populates="stories", foreign_keys=[created_by])
    story_for_emp = relationship("Employee", foreign_keys=[story_for])
    team          = relationship("Team", back_populates="stories", foreign_keys=[team_id])
    reactions     = relationship("StoryReaction", back_populates="story", cascade="all, delete-orphan")
    comments      = relationship("StoryComment", back_populates="story", cascade="all, delete-orphan")


class StoryComment(Base):
    __tablename__ = "story_comments"

    comment_id  = Column(Integer, primary_key=True, index=True)
    story_id    = Column(Integer, ForeignKey("success_stories.story_id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    body        = Column(Text, nullable=False)
    created_at  = Column(DateTime, server_default=func.now())

    story    = relationship("SuccessStory", back_populates="comments")
    employee = relationship("Employee")


class StoryReaction(Base):
    __tablename__ = "story_reactions"

    reaction_id  = Column(Integer, primary_key=True, index=True)
    story_id     = Column(Integer, ForeignKey("success_stories.story_id"), nullable=False)
    employee_id  = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    emoji        = Column(String(10), nullable=False)
    created_at   = Column(DateTime, server_default=func.now())

    story        = relationship("SuccessStory", back_populates="reactions")
    employee     = relationship("Employee")
