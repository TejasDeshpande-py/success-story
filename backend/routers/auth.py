from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import RegisterRequest, RegisterResponse, TokenResponse, LoginRequest
import backend.controllers.auth as auth_controller
import uuid, os
import httpx
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel
from typing import Literal
from backend.auth import get_current_user
from backend.limiter import limiter

router = APIRouter(tags=["Auth"])

# ---------------------------------------------------------------------------
# S3 client — instantiated once at module load, not per request
# ---------------------------------------------------------------------------
def _make_s3_client():
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

s3_client = _make_s3_client()

# ---------------------------------------------------------------------------
# Shared prompt fragments
# ---------------------------------------------------------------------------
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
    "someone": f"""You are an internal communications expert and professional editor \
specializing in employee storytelling.

Your task is to transform the given raw input into a polished, engaging \
peer recognition story suitable for internal newsletters or company blogs.

{_EDITORIAL_STANDARDS}

Storytelling Guidelines:
- Write in third person (use the person's name if mentioned, else he/she/they)
- Past tense throughout
- Keep the tone professional, warm, and appreciative — not dramatic
- Avoid exaggeration or adding information not in the input
- If the input lacks detail for a section, omit that section rather than inventing
- Assume the reader is a fellow employee who may not know this person's role
- Keep it concise — 80 to 150 words

Structure:
1. Strong opening — who this person is and what they did
2. How they approached it — skills, ownership, initiative
3. Concrete impact on the team, client, or business
4. Optional: a closing line of appreciation if present in the original

{_BANNED_PHRASES_INSTRUCTION}

Return only the final polished story. No headings, no commentary.""",

    "team": f"""You are an internal communications expert and professional editor \
specializing in employee storytelling.

Your task is to transform the given raw input into a polished, engaging \
team achievement story suitable for internal newsletters or company blogs.

{_EDITORIAL_STANDARDS}

Storytelling Guidelines:
- Write using 'we', 'our team', or 'the team'
- Past tense throughout
- Keep the tone professional, confident, and inspiring — not dramatic
- Avoid exaggeration or adding information not in the input
- If the input lacks detail for a section, omit that section rather than inventing
- Assume the reader is a fellow employee who may not know this team
- Keep it concise — 80 to 150 words

Structure:
1. Strong opening — what the team achieved and why it mattered
2. How the team approached it — collaboration, tools, method
3. Concrete outcome — delivery, time saved, client impact
4. Optional: a reflection or takeaway if present in the original

{_BANNED_PHRASES_INSTRUCTION}

Return only the final polished story. No headings, no commentary.""",

    "mine": f"""You are an internal communications expert and professional editor \
specializing in employee storytelling.

Your task is to transform the given raw input into a polished, engaging \
employee story suitable for internal newsletters or company blogs.

{_EDITORIAL_STANDARDS}
- Strictly preserve the author's personal voice
- Do not make it sound robotic or overly formal — the result should feel like \
the same person wrote it, just at their best

Storytelling Guidelines:
- Write in first person (I, my, me), past tense
- Keep the tone professional, warm, and inspiring — not overly dramatic
- Avoid exaggeration or adding information not present in the input
- If the input lacks enough detail to complete a section, omit that section \
rather than inventing content
- Assume the reader is a fellow employee who may not know the author's team or role
- Keep the story concise — 150 to 300 words

Structure:
1. Strong opening — a hook or context that draws the reader in
2. Journey — challenges, growth, and key experiences
3. Achievements or turning points
4. Reflection or takeaway

{_BANNED_PHRASES_INSTRUCTION}

Return only the final polished story. No headings, no commentary.""",
}

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class RephraseRequest(BaseModel):
    body: str
    story_type: Literal["mine", "someone", "team"] = "mine"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _contains_banned_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _BANNED_PHRASES_CHECK)


async def _call_groq(system_prompt: str, user_content: str) -> str:
    """Call Groq and return the assistant message text, or raise HTTPException."""
    groq_key = os.getenv("GROQ_API_KEY")
    async with httpx.AsyncClient() as client:
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
            timeout=30,
        )

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Groq API returned {r.status_code}: {r.text[:200]}",
        )

    d = r.json()
    if "choices" not in d:
        raise HTTPException(status_code=502, detail=f"Unexpected Groq response: {d}")

    return d["choices"][0]["message"]["content"].strip()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return auth_controller.register_user(payload, db)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    request.state.email_key = payload.email.lower()
    return auth_controller.login_user(payload.email, payload.password, db)


@router.post("/upload-picture")
def upload_picture(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),   # FIX: require authentication
):
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Only jpg, jpeg, png, webp allowed")

    filename = f"{uuid.uuid4()}{ext}"
    try:
        s3_client.upload_fileobj(
            file.file,
            os.getenv("AWS_BUCKET_NAME"),
            filename,
            ExtraArgs={"ContentType": file.content_type},
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {exc}")

    url = (
        f"https://{os.getenv('AWS_BUCKET_NAME')}"
        f".s3.{os.getenv('AWS_REGION')}.amazonaws.com/{filename}"
    )
    return {"url": url}


@router.post("/rephrase")
async def rephrase_story(
    payload: RephraseRequest,                 # FIX: typed Pydantic model, not raw dict
    current_user=Depends(get_current_user),
):
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Body is required")

    system_prompt = SYSTEM_PROMPTS[payload.story_type]
    user_content = f"Polish this success story:\n\n{body}"

    result = await _call_groq(system_prompt, user_content)

    # If the first attempt contains a banned phrase, retry once with a stricter nudge
    if _contains_banned_phrase(result):
        stricter_prompt = (
            system_prompt
            + "\n\nIMPORTANT: Your previous attempt used banned phrases. "
            "Re-write without any of the forbidden words listed above."
        )
        result = await _call_groq(stricter_prompt, user_content)

    # If the retry still fails, surface an error rather than silently returning raw input
    if _contains_banned_phrase(result):
        raise HTTPException(
            status_code=422,
            detail=(
                "The AI-generated story still contains restricted phrases after retry. "
                "Please try again or rephrase your input."
            ),
        )

    return {"rephrased_body": result}