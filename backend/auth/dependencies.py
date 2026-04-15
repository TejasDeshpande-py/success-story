from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.employee import Employee
from backend.auth.security import verify_password, decode_token
from jose import JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def authenticate_user(email: str, password: str, db: Session):
    user = db.query(Employee).filter(Employee.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Email not found")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    if user.status == "Pending":
        raise HTTPException(status_code=403, detail="Account pending approval")

    if user.status == "Rejected":
        raise HTTPException(status_code=403, detail="Account has been rejected")

    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(Employee).filter(Employee.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if user.status != "Active":
        raise HTTPException(status_code=403, detail="Account pending approval")

    return user

def require_hr_or_admin(current_user: Employee = Depends(get_current_user)):
    if current_user.role_id not in [1, 2]:
        raise HTTPException(status_code=403, detail="HR or Admin access required")
    return current_user