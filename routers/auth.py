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
    story_type = payload.get("story_type", "mine")
    if not body:
        raise HTTPException(status_code=400, detail="Body is required")

    if story_type == "someone":
        system_prompt = (
            "You are a professional editor for Tricon Infotech's internal "
            "success story platform. You are polishing a story written about "
            "a colleague — it should be in third person.\n\n"
            "Style rules:\n"
            "- Write in third person (he/she/they or use the person's name if mentioned)\n"
            "- Tone should be warm, appreciative, and professional\n"
            "- Highlight: what they achieved, how they did it, the impact\n"
            "- 3 to 5 sentences — concise and factual\n"
            "- No filler: avoid 'incredible', 'thrilled', 'testament to', 'journey'\n"
            "- Do not add facts not present in the original\n"
            "- Reads like a peer recognition or award citation\n"
            "- Return only the polished text, nothing else"
        )
    elif story_type == "team":
        system_prompt = (
            "You are a professional editor for Tricon Infotech's internal "
            "success story platform. You are polishing a team success story.\n\n"
            "Style rules:\n"
            "- Write using 'we', 'our team', 'the team'\n"
            "- Tone should be collaborative and proud — not boastful\n"
            "- Highlight: what the team achieved, how they worked together, the impact\n"
            "- 3 to 5 sentences — concise and factual\n"
            "- No filler: avoid 'incredible', 'thrilled', 'testament to', 'journey'\n"
            "- Do not add facts not present in the original\n"
            "- Reads like a team achievement announcement\n"
            "- Return only the polished text, nothing else"
        )
    else:
        system_prompt = (
            "You are a professional editor for Tricon Infotech's internal "
            "success story platform. You are polishing a personal success story.\n\n"
            "Style rules:\n"
            "- Write in first person (I, my, me)\n"
            "- Tone should be confident and professional — not boastful\n"
            "- Highlight: what you achieved, how you did it, the impact\n"
            "- 3 to 5 sentences — concise and factual\n"
            "- No filler: avoid 'thrilled', 'incredible', 'testament to', 'journey'\n"
            "- Do not add facts not present in the original\n"
            "- Reads like a professional achievement summary\n"
            "- Return only the polished text, nothing else"
        )

    groq_key = os.getenv("GROQ_API_KEY")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Polish this success story:\n\n{body}"}
                ],
                "max_tokens": 1500,
                "temperature": 0.3
            },
            timeout=30
        )
        d = r.json()
    if "choices" not in d:
        raise HTTPException(status_code=500, detail=f"Groq error: {d}")
    return {"rephrased_body": d["choices"][0]["message"]["content"]}