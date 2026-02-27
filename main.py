from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from model import Employee, SuccessStory
from schemas import TokenResponse, StoryCreate, StoryUpdate
from auth import authenticate_user, get_current_user, require_hr
from security import create_access_token

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Success Stories Platform"}


@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    try:
        count = db.query(Employee).count()
        return {
            "message": "Database connected",
            "employees_count": count
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token({
        "sub": user.email,
        "role_id": user.role_id
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/stories")
def get_published_stories(db: Session = Depends(get_db)):
    return db.query(SuccessStory).filter(
        SuccessStory.status == "Posted"
    ).all()


@app.get("/stories/{story_id}")
def get_story(story_id: int, db: Session = Depends(get_db)):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id,
        SuccessStory.status == "Posted"
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return story



@app.post("/stories", status_code=201)
def write_story(
    payload: StoryCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    story = SuccessStory(
        title=payload.title,
        designation=payload.designation,
        body=payload.body,
        ai_body=payload.ai_body,
        selected_body=payload.selected_body,
        status="Pending",
        extra=payload.extra,
        created_by=current_user.employee_id,
    )

    db.add(story)
    db.commit()
    db.refresh(story)

    return story


@app.get("/hr/stories/pending")
def get_pending_stories(
    db: Session = Depends(get_db),
    hr_user: Employee = Depends(require_hr),
):
    return db.query(SuccessStory).filter(
        SuccessStory.status == "Pending"
    ).all()


@app.patch("/hr/stories/{story_id}/publish")
def publish_story(
    story_id: int,
    db: Session = Depends(get_db),
    hr_user: Employee = Depends(require_hr),
):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status == "Posted":
        raise HTTPException(
            status_code=400,
            detail="Story already published"
        )

    story.status = "Posted"
    db.commit()
    db.refresh(story)

    return {
        "message": "Story published successfully",
        "story_id": story.story_id
    }