"""
Auth Service Layer: Business logic for authentication
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.models.employee import Employee
from backend.schemas.auth import RegisterRequest
from backend.auth.security import hash_password, create_access_token
from backend.auth.dependencies import authenticate_user
from typing import Dict


def register_user(payload: RegisterRequest, db: Session) -> Dict:
    """Register a new user with validation."""
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in payload.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in payload.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    
    existing = db.query(Employee.employee_id).filter(
        Employee.email == payload.email
    ).scalar()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_tricon = db.query(Employee.employee_id).filter(
        Employee.tricon_id == payload.tricon_id
    ).scalar()
    if existing_tricon:
        raise HTTPException(status_code=400, detail="tricon_id already taken")

    new_user = Employee(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        picture=payload.picture,
        tricon_id=payload.tricon_id,
        role_id=None,
        team_id=None,
        status="Pending",
    )
    db.add(new_user)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register user")

    db.refresh(new_user)

    return {
        "message": "Registration successful. Awaiting approval.",
        "employee_id": new_user.employee_id,
        "name": new_user.name,
        "email": new_user.email,
        "status": new_user.status,
    }


def login_user(email: str, password: str, db: Session) -> Dict:
    """Authenticate user and return access token."""
    user = authenticate_user(email, password, db)

    access_token = create_access_token({
        "sub": user.email,
        "user_id": user.employee_id,
        "role_id": user.role_id
    })

    return {"access_token": access_token, "token_type": "bearer"}
