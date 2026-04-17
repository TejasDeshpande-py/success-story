"""
Auth Router: HTTP endpoints for authentication
Delegates all business logic to backend.services.auth_service
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.schemas.auth import RegisterRequest, RegisterResponse, TokenResponse, LoginRequest
from backend.services import auth_service
import uuid
import os
import httpx
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, Field
from typing import Literal
from backend.auth.dependencies import get_current_user
from backend.middleware.limiter import limiter
from io import BytesIO
import re

router = APIRouter(tags=["Auth"])

# S3 client instantiated once at module load
def _make_s3_client():
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

s3_client = _make_s3_client()

# File upload constraints
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Editorial and prompt configuration
_EDITORIAL_STANDARDS = """Editorial Standards:
- Correct all grammar, spelling, and punctuation mistakes
- Enhance clarity, flow, and readability
- Strictly preserve the original meaning, facts, and voice
- Do not add new information or remove key details
- Do not make it sound robotic or overly formal"""

_BANNED_PHRASES_INSTRUCTION = (
    "Strictly avoid: 'exceptional', 'outstanding', 'valuable asset', "
    "'innovative approach', 'set a new standard', 'greatly improved', "
    "'instrumental', 'significant impact', 'testament to', 'thrilled', 'honored'"
)

_BANNED_PHRASES_CHECK = [
    "significant impact", "instrumental", "exceptional", "valuable asset",
    "driving success", "overall performance", "testament to", "thrilled",
    "honored", "passionate", "incredible", "revolutionary", "truly impactful",
    "outstanding", "set a new standard", "innovative approach", "greatly improved",
]

SYSTEM_PROMPTS = {
    "mine": f"""You are an internal communications expert and professional editor specializing in employee storytelling.

Your task is to transform the given raw input into a polished, engaging employee story suitable for internal newsletters or company blogs.

{_EDITORIAL_STANDARDS}
- Strictly preserve the author's personal voice
- Do not make it sound robotic or overly formal — the result should feel like the same person wrote it, just at their best

Storytelling Guidelines:
- Write in first person (I, my, me), past tense
- Keep the tone professional, warm, and inspiring — not overly dramatic
- Avoid exaggeration or adding information not present in the input
- If the input lacks enough detail to complete a section, omit that section rather than inventing content
- Assume the reader is a fellow employee who may not know the author's team or role
- Keep the story concise — 150 to 300 words

Structure (strictly follow this order based on the 4 inputs):
1. Background — set the scene in first person, what the situation was
2. Challenge — what made it difficult, in first person
3. Action — what you specifically did to tackle it
4. Outcome — the result and what it meant to you personally

{_BANNED_PHRASES_INSTRUCTION}

Return only the final polished story. No headings, no commentary.""",

    "someone": f"""You are an internal communications expert and professional editor specializing in employee storytelling.

Your task is to transform the given raw input into a polished, engaging peer recognition story suitable for internal newsletters or company blogs.

{_EDITORIAL_STANDARDS}

Storytelling Guidelines:
- Write in third person (use the person's name if mentioned, else he/she/they), past tense
- Keep the tone professional, warm, and appreciative — not dramatic
- Avoid exaggeration or adding information not in the input
- If the input lacks detail for a section, omit that section rather than inventing
- Assume the reader is a fellow employee who may not know this person's role
- Keep it concise — 150 to 300 words

Structure (strictly follow this order based on the 4 inputs):
1. Background — who this person is and what the situation was
2. Challenge — what obstacle or problem they faced
3. Action — what they did and how they approached it
4. Outcome — the concrete result and its impact

{_BANNED_PHRASES_INSTRUCTION}

Return only the final polished story. No headings, no commentary.""",

    "team": f"""You are an internal communications expert and professional editor specializing in employee storytelling.

Your task is to transform the given raw input into a polished, engaging team achievement story suitable for internal newsletters or company blogs.

{_EDITORIAL_STANDARDS}

Storytelling Guidelines:
- Write using 'we', 'our team', or 'the team', past tense
- Keep the tone professional, confident, and inspiring — not dramatic
- Avoid exaggeration or adding information not in the input
- If the input lacks detail for a section, omit that section rather than inventing
- Assume the reader is a fellow employee who may not know this team
- Keep it concise — 150 to 300 words

Structure (strictly follow this order based on the 4 inputs):
1. Background — what the team was working on and why it mattered
2. Challenge — what made it difficult for the team
3. Action — how the team collaborated and what was done
4. Outcome — what was achieved and its impact

{_BANNED_PHRASES_INSTRUCTION}

Return only the final polished story. No headings, no commentary.""",
}

# Request schemas
class RephraseRequest(BaseModel):
    background: str = Field(..., min_length=10, max_length=2000)
    challenge: str = Field(..., min_length=10, max_length=2000)
    action_taken: str = Field(..., min_length=10, max_length=2000)
    outcome: str = Field(..., min_length=10, max_length=2000)
    story_type: Literal["mine", "someone", "team"] = "mine"


def _contains_banned_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _BANNED_PHRASES_CHECK)


async def _call_groq(system_prompt: str, user_content: str) -> str:
    """Call Groq API. Timeout reduced to 10s to prevent DoS abuse."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.2,
                },
                timeout=10,  # FIX: was 30s — reduced to prevent DoS
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="AI service timed out. Please try again.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="AI service unavailable. Please try again later.")

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error. Please try again.",  # Don't leak Groq details to client
        )

    d = r.json()
    if "choices" not in d:
        raise HTTPException(status_code=502, detail="AI service returned unexpected response.")

    return d["choices"][0]["message"]["content"].strip()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("10/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    return auth_service.register_user(payload, db)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return access token."""
    request.state.email_key = payload.email.lower()
    return auth_service.login_user(payload.email, payload.password, db)


@router.post("/upload-picture")
@limiter.limit("10/minute")
async def upload_picture(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),   # FIX: was unauthenticated — anyone could upload
):
    """Upload profile picture to S3. Requires authentication."""

    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp allowed")

    # Read and size-check before doing anything else
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")

    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5MB.")

    # Validate it's actually an image (not just an extension rename)
    try:
        from PIL import Image
        img = Image.open(BytesIO(content))
        img.verify()  # Raises if not a valid image
    except Exception:
        raise HTTPException(status_code=400, detail="File is not a valid image")

    # Safe filename: never trust the original name
    safe_filename = f"{uuid.uuid4()}{ext}"

    try:
        s3_client.upload_fileobj(
            BytesIO(content),
            os.getenv("AWS_BUCKET_NAME"),
            safe_filename,
            ExtraArgs={
                "ContentType": file.content_type,
                "ServerSideEncryption": "AES256",
            },
        )
    except (BotoCoreError, ClientError):
        raise HTTPException(status_code=500, detail="Failed to upload image")

    url = (
        f"https://{os.getenv('AWS_BUCKET_NAME')}"
        f".s3.{os.getenv('AWS_REGION')}.amazonaws.com/{safe_filename}"
    )
    return {"url": url}


@router.post("/rephrase")
@limiter.limit("10/minute")
async def rephrase_story(
    request: Request,
    payload: RephraseRequest,
    current_user=Depends(get_current_user),
):
    """Use AI to rephrase story content."""
    system_prompt = SYSTEM_PROMPTS[payload.story_type]
    user_content = (
        f"Background:\n{payload.background.strip()}\n\n"
        f"Challenge:\n{payload.challenge.strip()}\n\n"
        f"Action Taken:\n{payload.action_taken.strip()}\n\n"
        f"Outcome:\n{payload.outcome.strip()}"
    )

    result = await _call_groq(system_prompt, user_content)

    if _contains_banned_phrase(result):
        stricter_prompt = (
            system_prompt
            + "\n\nIMPORTANT: Your previous attempt used banned phrases. "
            "Re-write without any of the forbidden words listed above."
        )
        result = await _call_groq(stricter_prompt, user_content)

    if _contains_banned_phrase(result):
        for phrase in _BANNED_PHRASES_CHECK:
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            result = pattern.sub("", result)

    result = re.sub(r"\s+([.,])", r"\1", result)
    result = re.sub(r"\s+", " ", result).strip()

    return {"rephrased_body": result}