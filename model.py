from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Employee(Base):
    __tablename__ = "employees"

    employee_id   = Column(Integer, primary_key=True, index=True)
    tricon_id     = Column(String(10), nullable=True, unique=True)
    name          = Column(String(120), nullable=False)
    email         = Column(String(160), unique=True, index=True, nullable=False)
    picture       = Column(String(500), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id       = Column(Integer, nullable=True, default=None)
    team_id       = Column(Integer, ForeignKey("teams.team_id"), nullable=True, default=None)
    status        = Column(Enum("Pending", "Active", "Rejected"), nullable=False, default="Pending")
    created_at    = Column(DateTime, server_default=func.now())
    created_by    = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    updated_at    = Column(DateTime, onupdate=func.now(), nullable=True)
    updated_by    = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)

    stories = relationship("SuccessStory", back_populates="creator", foreign_keys="[SuccessStory.created_by]")
    team    = relationship("Team", back_populates="employees", foreign_keys="[Employee.team_id]")

class Team(Base):
    __tablename__ = "teams"

    team_id    = Column(Integer, primary_key=True, index=True)
    team_name  = Column(String(120), nullable=False)
    team_picture = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    updated_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)

    employees  = relationship("Employee", back_populates="team", foreign_keys="[Employee.team_id]")
    stories    = relationship("SuccessStory", back_populates="team", foreign_keys="[SuccessStory.team_id]")


class SuccessStory(Base):
    __tablename__ = "success_stories"

    story_id      = Column(Integer, primary_key=True, index=True)
    title         = Column(String(200), nullable=False)
    designation   = Column(String(120), nullable=False)
    body          = Column(Text, nullable=False)
    ai_body       = Column(Text, nullable=False)
    selected_body = Column(Boolean, nullable=True, default=None)
    status        = Column(Enum("Pending", "Posted", "Rejected"), nullable=False, default="Pending")
    extra         = Column(String(500), nullable=True)
    story_picture = Column(String(500), nullable=True)
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