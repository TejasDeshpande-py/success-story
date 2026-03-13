from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from schemas import RegisterRequest, RegisterResponse, TokenResponse, LoginRequest
import controllers.auth as auth_controller
import shutil, uuid, os

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return auth_controller.register_user(payload, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_controller.login_user(payload.email, payload.password, db)


@router.post("/upload-picture")
def upload_picture(file: UploadFile = File(...)):
    allowed = [".jpg", ".jpeg", ".png", ".webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp allowed")
    filename = f"{uuid.uuid4()}{ext}"
    os.makedirs("static/uploads", exist_ok=True)
    path = f"static/uploads/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/static/uploads/{filename}"}