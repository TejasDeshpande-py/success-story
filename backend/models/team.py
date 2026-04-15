from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db.session import Base


class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(120), nullable=False)
    team_picture = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    updated_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)

    employees = relationship("Employee", back_populates="team", foreign_keys="[Employee.team_id]")
    stories = relationship("SuccessStory", back_populates="team", foreign_keys="[SuccessStory.team_id]")
