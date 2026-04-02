from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import RegisterRequest, RegisterResponse, TokenResponse, LoginRequest
import controllers.auth as auth_controller
import uuid, os
import httpx
import boto3
from auth import get_current_user

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
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp allowed")
    filename = f"{uuid.uuid4()}{ext}"
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
    except Exception:
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
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a professional corporate writer for Tricon Infotech. "
                            "Your job is to rewrite employee success stories in a compelling, "
                            "warm, and professional tone suitable for an internal company platform.\n\n"
                            "Rules:\n"
                            "- Keep ALL the same facts, names, projects, and outcomes from the original\n"
                            "- Do NOT add new facts or achievements that were not mentioned\n"
                            "- Write in first person (I, we, my, our)\n"
                            "- Make it engaging and human — not robotic or overly formal\n"
                            "- Use clear paragraphs with good flow\n"
                            "- Length should be similar to the original — do not pad or cut excessively\n"
                            "- Return only the rewritten story text, no headings, no explanations\n"
                            "- Avoid filler phrases like 'nothing short of remarkable', 'testament to', "
                            "'I'm thrilled', 'incredible journey' — these are corporate clichés\n"
                            "- Be concise — say more with fewer words\n"
                            "- Let the achievement speak for itself, don't over-explain the impact"
                        )
                    },
                    {"role": "user", "content": f"Rewrite this employee success story:\n\n{body}"}
                ],
                "max_tokens": 1500,
                "temperature": 0.5
            },
            timeout=30
        )
        d = r.json()
    if "choices" not in d:
        raise HTTPException(status_code=500, detail=f"Groq error: {d}")
    return {"rephrased_body": d["choices"][0]["message"]["content"]}