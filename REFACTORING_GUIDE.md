# SuccessStories Refactoring Guide
## From MVC to Layered Architecture

**Date:** April 14, 2026  
**Status:** Ready for Implementation  
**Custom Agent:** `/refactoring-enforcer`

---

## 📋 Project Structure After Refactoring

```
backend/
├── db/                          # ← NEW: Database connections
│   ├── __init__.py
│   └── session.py               # SessionLocal, get_db(), Base
├── models/                      # ← Moved from model.py
│   ├── __init__.py
│   ├── employee.py              # Employee table model
│   ├── team.py                  # Team table model
│   ├── story.py                 # SuccessStory & related models
│   └── story_reaction.py        # StoryReaction, StoryComment models
├── services/                    # ← NEW: ALL Business Logic
│   ├── __init__.py
│   ├── auth_service.py          # User registration, login, token logic
│   ├── stories_service.py       # Story CRUD, publishing, filtering
│   ├── users_service.py         # User data operations
│   ├── teams_service.py         # Team data operations
│   └── banners_service.py       # Banner data operations
├── routers/                     # ← ONLY HTTP Handling
│   ├── __init__.py
│   ├── auth.py                  # HTTP endpoints only (POST /register, /login)
│   ├── stories.py               # HTTP endpoints only (GET /stories, POST /create)
│   ├── users.py                 # HTTP endpoints only
│   ├── teams.py                 # HTTP endpoints only
│   └── banners.py               # HTTP endpoints only
├── schemas.py                   # ← Keep: Pydantic request/response models
├── security.py                  # ← Keep: hash_password, create_token
├── auth.py                      # ← Keep: get_current_user, decorators
├── limiter.py                   # ← Keep: Rate limiting setup
├── utils.py                     # ← Keep: Utility functions
├── main.py                      # ← Update: Include new router paths
├── database.py                  # ← REMOVE: Migrate to db/session.py
├── model.py                     # ← REMOVE: Migrate to models/
├── controllers/                 # ← REMOVE: Logic moves to services/
│   ├── auth.py                  # ❌ DELETE (→ services/auth_service.py)
│   ├── stories.py               # ❌ DELETE (→ services/stories_service.py)
│   ├── users.py                 # ❌ DELETE (→ services/users_service.py)
│   ├── teams.py                 # ❌ DELETE (→ services/teams_service.py)
│   └── banners.py               # ❌ DELETE (→ services/banners_service.py)
└── migrate.py                   # ← Keep: Migration utilities

```

---

## 📦 Layer Specification

### **Layer 1: `db/session.py` (Database Connections)**
**Responsibility:** Session and connection management ONLY  
**Should contain:**
- `DatabaseURL` configuration
- SQLAlchemy `engine` setup
- `SessionLocal` factory
- `Base` declarative class
- `get_db()` dependency injection function

**Should NOT contain:**
- ❌ ORM models
- ❌ Any business logic
- ❌ Query builders

**Example:**
```python
# backend/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://...")
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### **Layer 2: `models/` (Database Structure)**
**Responsibility:** ORM model definitions ONLY  
**Should contain:**
- SQLAlchemy `@declarative.mapped_class` definitions
- Column definitions with type hints
- Relationship definitions
- ✅ Database constraints & defaults

**Should NOT contain:**
- ❌ Business logic methods
- ❌ Database queries
- ❌ Any FastAPI dependencies
- ❌ Validation beyond DB schema

**File: `backend/models/employee.py`**
```python
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.session import Base

class Employee(Base):
    __tablename__ = "employees"
    
    employee_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(Enum("Pending", "Active", "Rejected"), default="Pending")
    created_at = Column(DateTime, server_default=func.now())
    
    stories = relationship("SuccessStory", back_populates="creator")
```

**File: `backend/models/story.py`**
```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.session import Base

class SuccessStory(Base):
    __tablename__ = "success_stories"
    
    story_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    challenge = Column(Text, nullable=False)
    action_taken = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("employees.employee_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    creator = relationship("Employee", back_populates="stories")
```

---

### **Layer 3: `services/` (Business Logic)**
**Responsibility:** ALL business logic and database operations  
**Should contain:**
- ✅ Database queries (`.query()`, `.filter()`, `.all()`, etc.)
- ✅ Business rule validation
- ✅ Data transformation & calculation
- ✅ Transaction management
- ✅ Error handling (`HTTPException`, custom exceptions)

**Should NOT contain:**
- ❌ FastAPI imports (APIRouter, HTTPException for structure)
- ❌ HTTP status codes (return data, let router handle status)
- ❌ Request/response schemas (routers handle these)
- ❌ Authentication decorators (`@require_hr`, etc.)

**File: `backend/services/auth_service.py`**
```python
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.employee import Employee
from security import hash_password, create_access_token
import re

def register_user(name: str, email: str, password: str, tricon_id: str, db: Session) -> dict:
    """Register new user with validation."""
    # Validation
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    if not any(c.isupper() for c in password):
        raise HTTPException(status_code=400, detail="Password needs uppercase")
    
    # Check existing
    if db.query(Employee).filter(Employee.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    new_user = Employee(
        name=name,
        email=email,
        password_hash=hash_password(password),
        tricon_id=tricon_id,
        status="Pending"
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")
    
    return {
        "message": "Registration successful",
        "employee_id": new_user.employee_id
    }

def login_user(email: str, password: str, db: Session) -> dict:
    """Authenticate user and return token."""
    user = db.query(Employee).filter(Employee.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.status != "Active":
        raise HTTPException(status_code=403, detail="User not activated")
    
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
```

**File: `backend/services/stories_service.py`**
```python
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc
from fastapi import HTTPException
from models.story import SuccessStory, StoryComment, StoryReaction
from models.employee import Employee
import math

ITEMS_PER_PAGE = 10

def get_published_stories(page: int, db: Session, current_user_id: int = None, 
                         search: str = None, sort_by: str = "recent") -> dict:
    """Retrieve published stories with sorting & search."""
    limit, offset = (ITEMS_PER_PAGE, (page - 1) * ITEMS_PER_PAGE)
    
    query = db.query(SuccessStory).filter(SuccessStory.status == "Posted")
    
    # Search
    if search:
        term = f"%{search.strip()}%"
        query = query.join(SuccessStory.creator).filter(Employee.name.ilike(term))
    
    # Sort
    if sort_by == "recent":
        query = query.order_by(SuccessStory.created_at.desc())
    elif sort_by == "oldest":
        query = query.order_by(SuccessStory.created_at.asc())
    elif sort_by == "views":
        query = query.order_by(SuccessStory.view_count.desc())
    
    total = query.count()
    stories = query.options(
        joinedload(SuccessStory.creator),
        joinedload(SuccessStory.reactions)
    ).offset(offset).limit(limit).all()
    
    return {
        "stories": [story_to_dict(s) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }

def create_story(title: str, challenge: str, action_taken: str, 
                result: str, db: Session, creator_id: int) -> dict:
    """Create new success story."""
    new_story = SuccessStory(
        title=title,
        challenge=challenge,
        action_taken=action_taken,
        result=result,
        created_by=creator_id,
        status="Draft"
    )
    db.add(new_story)
    try:
        db.commit()
        db.refresh(new_story)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create story")
    
    return story_to_dict(new_story)
```

---

### **Layer 4: `routers/` (HTTP Handling ONLY)**
**Responsibility:** HTTP request/response handling and dependency injection  
**Should contain:**
- ✅ FastAPI route handlers
- ✅ HTTP status codes
- ✅ Request/response schema validation
- ✅ Authentication/authorization checks
- ✅ Dependency injection (`Depends()`)
- ✅ Error handling (catch exceptions, return HTTP status)

**Should NOT contain:**
- ❌ Database queries (`.query()`, `.filter()`, etc.)
- ❌ Business logic (calculations, validations beyond schema)
- ❌ ORM model logic
- ❌ Business rule enforcement (move to services)

**File: `backend/routers/auth.py` (AFTER Refactoring)**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import RegisterRequest, LoginRequest, TokenResponse
from db.session import get_db
from services import auth_service
from auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register new user."""
    try:
        result = auth_service.register_user(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            tricon_id=payload.tricon_id,
            db=db
        )
        return result
    except HTTPException:
        raise

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """User login."""
    try:
        result = auth_service.login_user(
            email=payload.email,
            password=payload.password,
            db=db
        )
        return result
    except HTTPException:
        raise

@router.get("/me")
def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user info."""
    return {
        "employee_id": current_user.employee_id,
        "name": current_user.name,
        "email": current_user.email
    }
```

**File: `backend/routers/stories.py` (AFTER Refactoring)**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from schemas import StoryCreate, StoryResponse
from db.session import get_db
from services import stories_service
from auth import get_current_user, require_hr_or_admin
from models.employee import Employee

router = APIRouter(prefix="/stories", tags=["Stories"])

@router.get("/", response_model=dict)
def get_published_stories(
    page: int = 1,
    search: Optional[str] = None,
    sort_by: Optional[str] = "recent",
    db: Session = Depends(get_db)
):
    """Get published stories."""
    try:
        return stories_service.get_published_stories(
            page=page,
            search=search,
            sort_by=sort_by,
            db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch stories")

@router.post("/create", response_model=StoryResponse, status_code=201)
def create_story(
    payload: StoryCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Create new story."""
    try:
        return stories_service.create_story(
            title=payload.title,
            challenge=payload.challenge,
            action_taken=payload.action_taken,
            result=payload.result,
            db=db,
            creator_id=current_user.employee_id
        )
    except HTTPException:
        raise

@router.get("/mine")
def get_my_stories(
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Get current user's stories."""
    return stories_service.get_user_stories(
        user_id=current_user.employee_id,
        page=page,
        db=db
    )
```

---

## 🔄 Refactoring Workflow

### Step 1: Create `/db/` folder structure
```bash
mkdir backend/db
touch backend/db/__init__.py
touch backend/db/session.py
```
Move content from `backend/database.py` to `backend/db/session.py`

### Step 2: Create `/services/` folder structure  
```bash
mkdir backend/services
touch backend/services/__init__.py
touch backend/services/auth_service.py
touch backend/services/stories_service.py
touch backend/services/users_service.py
touch backend/services/teams_service.py
touch backend/services/banners_service.py
```

### Step 3: Create `/models/` folder structure
```bash
mkdir backend/models
touch backend/models/__init__.py
touch backend/models/employee.py
touch backend/models/team.py
touch backend/models/story.py
touch backend/models/story_reaction.py
```
Move models from `backend/model.py`

### Step 4: Migrate business logic
Move functions from `backend/controllers/*.py` to `backend/services/*.py`

### Step 5: Clean routers
Remove business logic from `backend/routers/*.py`, keep only HTTP handling

### Step 6: Update imports
Update all imports in main.py and routers to use new paths

### Step 7: Delete old files
- Remove `backend/database.py`
- Remove `backend/model.py`
- Remove `backend/controllers/` directory

---

## ✅ Validation Checklist

- [ ] No database queries in `routers/*.py` files
- [ ] All `db.query()` calls in `services/*.py` files
- [ ] No business logic in `routers/*.py` files
- [ ] Services functions have type hints on all parameters
- [ ] Router functions return service method results directly
- [ ] No circular imports between services
- [ ] `db/session.py` has only connection code
- [ ] `models/*.py` have only ORM definitions
- [ ] All imports updated to use new paths
- [ ] `main.py` includes all routers correctly
- [ ] No Python errors or import failures

---

## 📌 Key Rules to Remember

1. **Routers** = Request → Service → Response (5-10 lines max)
2. **Services** = Business logic + DB operations (can be many lines)
3. **Models** = Pure ORM definitions (no methods)
4. **DB** = Only connection & session setup
5. **Schemas** = Pydantic request/response models (unchanged)

---

**Use the `/refactoring-enforcer` agent to validate each step!**
