from fastapi import HTTPException
from sqlalchemy.orm import Session
from model import Employee
from schemas import RegisterRequest
from security import hash_password, create_access_token
from auth import authenticate_user


def register_user(payload: RegisterRequest, db: Session):
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
    except Exception:
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
       


def login_user(username: str, password: str, db: Session):
    user = authenticate_user(username, password, db)

    access_token = create_access_token({
        "sub": user.email,
        "user_id": user.employee_id,
        "role_id": user.role_id
    })

    return {"access_token": access_token, "token_type": "bearer"}