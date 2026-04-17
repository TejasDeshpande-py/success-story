from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.employee import Employee
from backend.auth.security import verify_password, decode_token
from jose import JWTError
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Role constants — no more magic numbers scattered across codebase
ROLE_ADMIN = 1
ROLE_HR = 2


def authenticate_user(email: str, password: str, db: Session) -> Employee:
    """
    Authenticate user credentials.
    Intentionally returns the same 401 for both bad email and bad password
    to prevent user enumeration attacks.
    """
    user = db.query(Employee).filter(Employee.email == email).first()

    # Always run verify_password even if user not found (prevents timing attacks)
    dummy_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
    password_ok = verify_password(password, user.password_hash if user else dummy_hash)

    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status == "Pending":
        raise HTTPException(status_code=403, detail="Account pending approval")

    if user.status == "Rejected":
        raise HTTPException(status_code=403, detail="Account has been rejected")

    if user.status != "Active":
        raise HTTPException(status_code=403, detail="Account is not active")

    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Employee:
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(Employee).filter(Employee.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    if user.status != "Active":
        raise HTTPException(status_code=403, detail="Account is not active")

    return user


def get_optional_user(
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[Employee]:
    """
    Returns current user if token is valid, None otherwise.
    Used for endpoints that work for both authenticated and anonymous users.
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        email: str = payload.get("sub")
        if not email:
            return None
        user = db.query(Employee).filter(Employee.email == email).first()
        return user if user and user.status == "Active" else None
    except (JWTError, Exception):
        return None


def require_hr_or_admin(
    current_user: Employee = Depends(get_current_user)
) -> Employee:
    if current_user.role_id not in [ROLE_ADMIN, ROLE_HR]:
        raise HTTPException(status_code=403, detail="HR or Admin access required")
    return current_user