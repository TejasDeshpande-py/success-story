from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.db.session import Base


class Banner(Base):
    __tablename__ = "banners"

    banner_id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(500), nullable=False)
    title = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)


class BannerImage(Base):
    __tablename__ = "banner_images"

    banner_id = Column(Integer, primary_key=True, index=True)
    slot = Column(Integer, nullable=False, unique=True)
    image_url = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    updated_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
