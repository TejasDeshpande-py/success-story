from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base

class Employee(Base):
    __tablename__ = "employees"

    employee_id   = Column(Integer, primary_key=True, index=True)
    name          = Column(String(120), nullable=False)
    email         = Column(String(160), unique=True, index=True, nullable=False)
    picture       = Column(String(500))
    password_hash = Column(String(255), nullable=False)
    role_id       = Column(Integer, nullable=False)
    type          = Column(Enum('individual', 'group'), default='individual')
    team_id       = Column(Integer, nullable=False)

    stories = relationship("SuccessStory", back_populates="creator")


class SuccessStory(Base):
    __tablename__ = "success_stories"

    story_id      = Column(Integer, primary_key=True, index=True)
    title         = Column(String(200), nullable=False)
    designation   = Column(String(120))
    body          = Column(Text, nullable=False)
    ai_body       = Column(Text, nullable=False)
    selected_body = Column(Text, nullable=True)
    status        = Column(String(20), nullable=False, default="Pending")
    extra         = Column(String(500))
    created_by    = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)

    creator = relationship("Employee", back_populates="stories")