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
            "You are a senior communications writer at a top tech company. "
            "Your job is to rewrite peer recognition stories for internal awards. "
            "Rewrite in third person (he/she/they or the person's name if mentioned).\n\n"
            "The story must:\n"
            "- Open with who did what and the scale of the achievement\n"
            "- Explain briefly how they approached it — skill, ownership, initiative\n"
            "- End with the concrete impact on the team or business\n"
            "- Be 3 to 4 sentences, warm but grounded in facts\n"
            "- Sound like a manager nominating someone for an award\n"
            "- Use active voice throughout\n"
            "- Avoid clichés: no 'thrilled', 'honored', 'testament to', 'journey', "
            "'passionate', 'incredible', 'revolutionary', 'truly impactful'\n"
            "- Do not invent facts not present in the original\n"
            "- Return only the rewritten story, no preamble or explanation"
        )
    elif story_type == "team":
        system_prompt = (
            "You are a senior communications writer at a top tech company. "
            "Your job is to rewrite team achievement stories for internal recognition. "
            "Rewrite using 'we', 'our team', 'the team'.\n\n"
            "The story must:\n"
            "- Open with what the team achieved and why it mattered\n"
            "- Explain how the team collaborated or what approach they took\n"
            "- End with the concrete outcome — delivery, savings, efficiency, or impact\n"
            "- Be 3 to 4 sentences, confident and specific\n"
            "- Sound like a team lead announcing a win to the company\n"
            "- Use active voice throughout\n"
            "- Avoid clichés: no 'thrilled', 'honored', 'testament to', 'journey', "
            "'passionate', 'incredible', 'revolutionary', 'truly impactful'\n"
            "- Do not invent facts not present in the original\n"
            "- Return only the rewritten story, no preamble or explanation"
        )
    else:
        system_prompt = (
            "You are a senior communications writer at a top tech company. "
            "Your job is to rewrite employee success stories for internal recognition. "
            "Rewrite in first person (I, my, me).\n\n"
            "The story must:\n"
            "- Open with the specific achievement and its scale or impact\n"
            "- Explain briefly how it was done (tools, approach, ownership)\n"
            "- End with the concrete outcome — time saved, efficiency gained, or business value\n"
            "- Be 3 to 4 sentences, tight and confident\n"
            "- Sound like a high-performer writing their own award citation\n"
            "- Use active voice throughout\n"
            "- Avoid clichés: no 'thrilled', 'honored', 'testament to', 'journey', "
            "'passionate', 'incredible', 'revolutionary', 'truly impactful'\n"
            "- Do not invent facts not present in the original\n"
            "- Return only the rewritten story, no preamble or explanation"
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
                "temperature": 0.2
            },
            timeout=30
        )
        d = r.json()
    if "choices" not in d:
        raise HTTPException(status_code=500, detail=f"Groq error: {d}")
    return {"rephrased_body": d["choices"][0]["message"]["content"]}