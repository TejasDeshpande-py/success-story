from fastapi import APIRouter, Depends, UploadFile, File,HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
from schemas import RegisterRequest, RegisterResponse, TokenResponse, LoginRequest
import controllers.auth as auth_controller
import shutil, uuid, os
import httpx
from auth import get_current_user

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return auth_controller.register_user(payload, db)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_controller.login_user(payload.email, payload.password, db)


@router.post("/upload-picture")
def upload_picture(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    allowed = [".jpg", ".jpeg", ".png", ".webp"]
    allowed_mime = ["image/jpeg", "image/png", "image/webp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp allowed")
    if file.content_type not in allowed_mime:
        raise HTTPException(status_code=400, detail="Invalid file type — only JPG, PNG, WEBP allowed")
    contents = file.file.read(10 * 1024 * 1024 + 1)
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 10MB")
    file.file.seek(0)

    filename = f"{uuid.uuid4()}{ext}"
    
    import boto3
    from dotenv import load_dotenv
    load_dotenv()
    
    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    try:
        s3.upload_fileobj(
            file.file,
            os.getenv("AWS_BUCKET_NAME"),
            filename,
            ExtraArgs={"ContentType": file.content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload image")
    
    url = f"https://{os.getenv('AWS_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{filename}"
    return {"url": url}


@router.post("/rephrase")
async def rephrase_story(payload: dict, current_user=Depends(get_current_user)):
    body = payload.get("body", "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Body is required")
    
    groq_key = os.getenv("GROQ_API_KEY")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": "You are a professional writer. Rephrase the given employee success story to make it more impactful, professional and engaging. Keep it first person. Return only the rephrased story, nothing else."},
                    {"role": "user", "content": body}
                ],
                "max_tokens": 1000
            },
            timeout=30
        )
        d = r.json()
    
    if "choices" not in d:
        raise HTTPException(status_code=500, detail=f"Groq error: {d}")
    return {"rephrased": d["choices"][0]["message"]["content"]}