from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from model import Employee
from security import verify_password, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def authenticate_user(email: str, password: str, db: Session):
    user = db.query(Employee).filter(Employee.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(Employee).filter(Employee.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def require_hr(current_user: Employee = Depends(get_current_user)):
    if current_user.role_id != 1:
        raise HTTPException(status_code=403, detail="HR access required")
    return current_user