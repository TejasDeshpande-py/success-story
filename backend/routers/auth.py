from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import RegisterRequest, RegisterResponse, TokenResponse, LoginRequest
import backend.controllers.auth as auth_controller
import uuid, os
import httpx
import boto3
from backend.auth import get_current_user
from backend.limiter import limiter

router = APIRouter(tags=["Auth"])

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return auth_controller.register_user(payload, db)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    request.state.email_key = payload.email.lower()
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
            "You are an internal communications expert and professional editor "
            "specializing in employee storytelling.\n\n"
            "Your task is to transform the given raw input into a polished, engaging "
            "peer recognition story suitable for internal newsletters or company blogs.\n\n"
            "Editorial Standards:\n"
            "- Correct all grammar, spelling, and punctuation mistakes\n"
            "- Enhance clarity, flow, and readability\n"
            "- Strictly preserve the original meaning, facts, and voice\n"
            "- Do not add new information or remove key details\n"
            "- Do not make it sound robotic or overly formal\n\n"
            "Storytelling Guidelines:\n"
            "- Write in third person (use the person's name if mentioned, else he/she/they)\n"
            "- Past tense throughout\n"
            "- Keep the tone professional, warm, and appreciative — not dramatic\n"
            "- Avoid exaggeration or adding information not in the input\n"
            "- If the input lacks detail for a section, omit that section rather than inventing\n"
            "- Assume the reader is a fellow employee who may not know this person's role\n"
            "- Keep it concise — 80 to 150 words\n\n"
            "Structure:\n"
            "1. Strong opening — who this person is and what they did\n"
            "2. How they approached it — skills, ownership, initiative\n"
            "3. Concrete impact on the team, client, or business\n"
            "4. Optional: a closing line of appreciation if present in the original\n\n"
            "Strictly avoid: 'exceptional', 'outstanding', 'valuable asset', "
            "'innovative approach', 'set a new standard', 'greatly improved', "
            "'instrumental', 'significant impact', 'testament to', 'thrilled', 'honored'\n\n"
            "Return only the final polished story. No headings, no commentary."
        )
    elif story_type == "team":
        system_prompt = (
            "You are an internal communications expert and professional editor "
            "specializing in employee storytelling.\n\n"
            "Your task is to transform the given raw input into a polished, engaging "
            "team achievement story suitable for internal newsletters or company blogs.\n\n"
            "Editorial Standards:\n"
            "- Correct all grammar, spelling, and punctuation mistakes\n"
            "- Enhance clarity, flow, and readability\n"
            "- Strictly preserve the original meaning, facts, and voice\n"
            "- Do not add new information or remove key details\n"
            "- Do not make it sound robotic or overly formal\n\n"
            "Storytelling Guidelines:\n"
            "- Write using 'we', 'our team', or 'the team'\n"
            "- Past tense throughout\n"
            "- Keep the tone professional, confident, and inspiring — not dramatic\n"
            "- Avoid exaggeration or adding information not in the input\n"
            "- If the input lacks detail for a section, omit that section rather than inventing\n"
            "- Assume the reader is a fellow employee who may not know this team\n"
            "- Keep it concise — 80 to 150 words\n\n"
            "Structure:\n"
            "1. Strong opening — what the team achieved and why it mattered\n"
            "2. How the team approached it — collaboration, tools, method\n"
            "3. Concrete outcome — delivery, time saved, client impact\n"
            "4. Optional: a reflection or takeaway if present in the original\n\n"
            "Strictly avoid: 'exceptional', 'outstanding', 'valuable asset', "
            "'innovative approach', 'set a new standard', 'greatly improved', "
            "'instrumental', 'significant impact', 'testament to', 'thrilled', 'honored'\n\n"
            "Return only the final polished story. No headings, no commentary."
        )
    else:
        system_prompt = (
            "You are an internal communications expert and professional editor "
            "specializing in employee storytelling.\n\n"
            "Your task is to transform the given raw input into a polished, engaging "
            "employee story suitable for internal newsletters or company blogs.\n\n"
            "Editorial Standards:\n"
            "- Correct all grammar, spelling, and punctuation mistakes\n"
            "- Enhance clarity, flow, and readability\n"
            "- Strictly preserve the original meaning, facts, and the author's personal voice\n"
            "- Do not add new information or remove key details\n"
            "- Do not make it sound robotic or overly formal — the result should feel like "
            "the same person wrote it, just at their best\n\n"
            "Storytelling Guidelines:\n"
            "- Write in first person (I, my, me), past tense\n"
            "- Keep the tone professional, warm, and inspiring — not overly dramatic\n"
            "- Avoid exaggeration or adding information not present in the input\n"
            "- If the input lacks enough detail to complete a section, omit that section "
            "rather than inventing content\n"
            "- Assume the reader is a fellow employee who may not know the author's team or role\n"
            "- Keep the story concise — 150 to 300 words\n\n"
            "Structure:\n"
            "1. Strong opening — a hook or context that draws the reader in\n"
            "2. Journey — challenges, growth, and key experiences\n"
            "3. Achievements or turning points\n"
            "4. Reflection or takeaway\n\n"
            "Strictly avoid: 'exceptional', 'outstanding', 'valuable asset', "
            "'innovative approach', 'set a new standard', 'greatly improved', "
            "'instrumental', 'significant impact', 'testament to', 'thrilled', 'honored'\n\n"
            "Return only the final polished story. No headings, no commentary."
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
    bad_phrases = [
        "significant impact", "instrumental", "exceptional", "valuable asset",
        "driving success", "overall performance", "testament to", "thrilled",
        "honored", "passionate", "incredible", "revolutionary", "truly impactful",
        "outstanding", "set a new standard", "innovative approach", "greatly improved"
    ]

    def is_bad_output(text: str):
        t = text.lower()
        for phrase in bad_phrases:
            if phrase in t:
                return True
        return False

    result = d["choices"][0]["message"]["content"].strip()
    if is_bad_output(result):
        result = body
    return {"rephrased_body": result}