from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db import Base


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
