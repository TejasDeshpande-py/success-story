from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from model import Employee, SuccessStory
from schemas import (
    TokenResponse, StoryCreate, StoryResponse,
    StoryPublicResponse, PublishResponse, RejectResponse,
    SelectBodyRequest, RegisterRequest, RegisterResponse,
    EmployeeStoryUpdate, HRStoryUpdate,
    ApproveUserRequest, UserResponse
)
from auth import authenticate_user, get_current_user, require_hr_or_admin
from security import create_access_token, hash_password

app = FastAPI()


# ─── Public Routes ────────────────────────────────────────────────────────────
@app.get("/")
def greet():
    return {"message" : "Hello"}
@app.get("/stories", response_model=List[StoryPublicResponse])
def get_stories(page: int = 1, db: Session = Depends(get_db)):
    limit = 10
    offset = (page - 1) * limit
    stories = db.query(SuccessStory).filter(
        SuccessStory.status == "Posted"
    ).offset(offset).limit(limit).all()

    return [
        {
            "story_id": story.story_id,
            "title": story.title,
            "designation": story.designation,
            "selected_body": story.selected_body,
            "extra": story.extra,
            "name": story.creator.name,
            "picture": story.creator.picture
        }
        for story in stories
    ]


@app.get("/stories/{story_id}", response_model=StoryPublicResponse)
def get_story(story_id: int, db: Session = Depends(get_db)):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id,
        SuccessStory.status == "Posted"
    ).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return {
        "story_id": story.story_id,
        "title": story.title,
        "designation": story.designation,
        "selected_body": story.selected_body,
        "extra": story.extra,
        "name": story.creator.name,
        "picture": story.creator.picture
    }


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Employee).filter(Employee.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = Employee(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        picture=payload.picture,
        type=payload.type,
        role_id=None,
        team_id=None,
        status="Pending",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Registration successful. Awaiting approval.",
        "employee_id": new_user.employee_id,
        "name": new_user.name,
        "email": new_user.email,
        "type": new_user.type,
        "status": new_user.status,
    }


@app.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(form_data.username, form_data.password, db)

    access_token = create_access_token({
        "sub": user.email,
        "user_id": user.employee_id,
        "role_id": user.role_id
    })

    return {"access_token": access_token, "token_type": "bearer"}


# ─── Employee Routes (role_id: 0) ─────────────────────────────────────────────

@app.post("/stories/create", response_model=StoryResponse, status_code=201)
def create_story(
    payload: StoryCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    story = SuccessStory(
        title=payload.title,
        designation=payload.designation,
        body=payload.body,
        ai_body=payload.ai_body,
        selected_body=None,
        status="Pending",
        extra=payload.extra,
        created_by=current_user.employee_id,
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    return {
        "story_id": story.story_id,
        "title": story.title,
        "designation": story.designation,
        "body": story.body,
        "ai_body": story.ai_body,
        "selected_body": story.selected_body,
        "status": story.status,
        "extra": story.extra,
        "created_by": story.created_by,
        "name": current_user.name,
        "picture": current_user.picture
    }


@app.patch("/stories/{story_id}", response_model=StoryResponse)
def edit_story(
    story_id: int,
    payload: EmployeeStoryUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.created_by != current_user.employee_id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this story")

    if story.status not in ["Pending", "Rejected"]:
        raise HTTPException(status_code=400, detail="You can only edit Pending or Rejected stories")

    story.body = payload.body
    db.commit()
    db.refresh(story)

    return {
        "story_id": story.story_id,
        "title": story.title,
        "designation": story.designation,
        "body": story.body,
        "ai_body": story.ai_body,
        "selected_body": story.selected_body,
        "status": story.status,
        "extra": story.extra,
        "created_by": story.created_by,
        "name": current_user.name,
        "picture": current_user.picture
    }


# ─── HR + Admin Routes (role_id: 1 & 2) ──────────────────────────────────────

@app.get("/users", response_model=List[UserResponse])
def get_all_users(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    limit = 10
    offset = (page - 1) * limit
    return db.query(Employee).filter(
        Employee.status == "Active"
    ).offset(offset).limit(limit).all()


@app.get("/users/pending", response_model=List[UserResponse])
def get_pending_users(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    limit = 10
    offset = (page - 1) * limit
    return db.query(Employee).filter(
        Employee.status == "Pending"
    ).offset(offset).limit(limit).all()


@app.patch("/users/{employee_id}/approve", response_model=UserResponse)
def approve_user(
    employee_id: int,
    payload: ApproveUserRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    user = db.query(Employee).filter(
        Employee.employee_id == employee_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "Pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    if payload.role_id == 2:
        raise HTTPException(status_code=403, detail="Cannot assign Super Admin role")

    user.role_id = payload.role_id
    user.status = "Active"
    db.commit()
    db.refresh(user)
    return user


@app.patch("/users/{employee_id}/reject", response_model=UserResponse)
def reject_user(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    user = db.query(Employee).filter(
        Employee.employee_id == employee_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "Pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    user.status = "Rejected"
    db.commit()
    db.refresh(user)
    return user


@app.get("/stories/pending", response_model=List[StoryResponse])
def get_pending_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    limit = 10
    offset = (page - 1) * limit
    stories = db.query(SuccessStory).filter(
        SuccessStory.status == "Pending"
    ).offset(offset).limit(limit).all()

    return [
        {
            "story_id": story.story_id,
            "title": story.title,
            "designation": story.designation,
            "body": story.body,
            "ai_body": story.ai_body,
            "selected_body": story.selected_body,
            "status": story.status,
            "extra": story.extra,
            "created_by": story.created_by,
            "name": story.creator.name,
            "picture": story.creator.picture
        }
        for story in stories
    ]


@app.get("/stories/rejected", response_model=List[StoryResponse])
def get_rejected_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    limit = 10
    offset = (page - 1) * limit
    stories = db.query(SuccessStory).filter(
        SuccessStory.status == "Rejected"
    ).offset(offset).limit(limit).all()

    return [
        {
            "story_id": story.story_id,
            "title": story.title,
            "designation": story.designation,
            "body": story.body,
            "ai_body": story.ai_body,
            "selected_body": story.selected_body,
            "status": story.status,
            "extra": story.extra,
            "created_by": story.created_by,
            "name": story.creator.name,
            "picture": story.creator.picture
        }
        for story in stories
    ]


@app.patch("/stories/{story_id}/edit", response_model=StoryResponse)
def hr_edit_story(
    story_id: int,
    payload: HRStoryUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)

    db.commit()
    db.refresh(story)

    return {
        "story_id": story.story_id,
        "title": story.title,
        "designation": story.designation,
        "body": story.body,
        "ai_body": story.ai_body,
        "selected_body": story.selected_body,
        "status": story.status,
        "extra": story.extra,
        "created_by": story.created_by,
        "name": story.creator.name,
        "picture": story.creator.picture
    }


@app.patch("/stories/{story_id}/select-body", response_model=StoryResponse)
def select_body(
    story_id: int,
    payload: SelectBodyRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can have body selected")

    if payload.choice == "original":
        story.selected_body = False
    elif payload.choice == "ai":
        story.selected_body = True
    else:
        raise HTTPException(status_code=400, detail="Choice must be 'original' or 'ai'")

    db.commit()
    db.refresh(story)

    return {
        "story_id": story.story_id,
        "title": story.title,
        "designation": story.designation,
        "body": story.body,
        "ai_body": story.ai_body,
        "selected_body": story.selected_body,
        "status": story.status,
        "extra": story.extra,
        "created_by": story.created_by,
        "name": story.creator.name,
        "picture": story.creator.picture
    }


@app.patch("/stories/{story_id}/publish", response_model=PublishResponse)
def publish_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
):
    story = db.query(SuccessStory).filter(
        SuccessStory.story_id == story_id
    ).first()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending stories can be published")

    if story.selected_body is None:
        raise HTTPException(status_code=400, detail="A body must be selected before publishing")

    story.status = "Posted"
    db.commit()
    db.refresh(story)
    return {"message": "Story published successfully", "story_id": story.story_id}


@app.patch("/stories/{story_id}/reject", response_model=RejectResponse)
def reject_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_hr_or_admin),
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
    return {"message": "Story rejected successfully", "story_id": story.story_id}
