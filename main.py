from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from model import Employee, SuccessStory
from schemas import (
    TokenResponse, StoryCreate, StoryResponse,
    StoryPublicResponse, PublishResponse, RejectResponse,
    SelectBodyRequest, RegisterRequest, RegisterResponse
)
from auth import authenticate_user, get_current_user, require_hr
from security import create_access_token, hash_password

app = FastAPI()


@app.get("/", response_model=List[StoryPublicResponse])
def root(
    page: int = 1,
    db: Session = Depends(get_db)
):
    limit = 10
    offset = (page - 1) * limit
    return db.query(SuccessStory).filter(
        SuccessStory.status == "Posted"
    ).offset(offset).limit(limit).all()


@app.get("/stories/{story_id}", response_model=StoryPublicResponse)
def get_story(story_id: int, db: Session = Depends(get_db)):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id,
        SuccessStory.status == "Posted"
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return story


# auth

@app.post("/register", response_model=RegisterResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    if payload.role_id not in [0, 1]:
        raise HTTPException(status_code=400, detail="Invalid role. Use 0 for Employee or 1 for HR")

    existing = db.query(Employee).filter(Employee.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = Employee(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        team_id=1,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "employee_id": new_user.employee_id,
        "email": new_user.email,
        "role_id": new_user.role_id
    }


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

    access_token = create_access_token({"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

#write story

@app.post("/stories", response_model=StoryResponse, status_code=201)
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


# hr

@app.get("/hr/stories/pending", response_model=List[StoryResponse])
def get_pending_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    hr_user: Employee = Depends(require_hr),
):
    limit = 10
    offset = (page - 1) * limit
    return db.query(SuccessStory).filter(
        SuccessStory.status == "Pending"
    ).offset(offset).limit(limit).all()


@app.get("/hr/stories/rejected", response_model=List[StoryResponse])
def get_rejected_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    hr_user: Employee = Depends(require_hr),
):
    limit = 10
    offset = (page - 1) * limit
    return db.query(SuccessStory).filter(
        SuccessStory.status == "Rejected"
    ).offset(offset).limit(limit).all()


@app.patch("/hr/stories/{story_id}/select-body", response_model=StoryResponse)
def select_body(
    story_id: int,
    payload: SelectBodyRequest,
    db: Session = Depends(get_db),
    hr_user: Employee = Depends(require_hr),
):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can be edited")

    if payload.choice == "original":
        story.selected_body = story.body
    elif payload.choice == "ai":
        story.selected_body = story.ai_body
    else:
        raise HTTPException(status_code=400, detail="Choice must be 'original' or 'ai'")

    db.commit()
    db.refresh(story)

    return story


@app.patch("/hr/stories/{story_id}/publish", response_model=PublishResponse)
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

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can be published")

    if not story.selected_body:
        raise HTTPException(status_code=400, detail="A body must be selected before publishing")

    story.status = "Posted"
    db.commit()
    db.refresh(story)

    return {
        "message": "Story published successfully",
        "story_id": story.story_id
    }


@app.patch("/hr/stories/{story_id}/reject", response_model=RejectResponse)
def reject_story(
    story_id: int,
    db: Session = Depends(get_db),
    hr_user: Employee = Depends(require_hr),
):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can be rejected")

    story.status = "Rejected"
    db.commit()
    db.refresh(story)

    return {
        "message": "Story rejected successfully",
        "story_id": story.story_id
    }
