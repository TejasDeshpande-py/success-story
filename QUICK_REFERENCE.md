# Quick Reference: Layer Specifications

## 🎯 Layer Responsibilities at a Glance

| Layer | Location | Purpose | Contains | Does NOT Contain |
|-------|----------|---------|----------|------------------|
| **routers/** | `backend/routers/` | HTTP request/response handling | FastAPI routes, status codes, schema validation, auth checks | DB queries, business logic, ORM operations |
| **services/** | `backend/services/` | ALL business logic & data ops | DB queries, validation, calculations, transactions | FastAPI imports, HTTP status codes, routers |
| **models/** | `backend/models/` | Database structure definitions | SQLAlchemy ORM models, columns, relationships, constraints | Methods, business logic, logic functions |
| **db/** | `backend/db/session.py` | Database connection management | SessionLocal, engine, Base, get_db() dependency | ORM models, queries, business logic |

---

## 📝 Function Length Rules

| Layer | Lines | Reason |
|-------|-------|--------|
| Router functions | **5-10** | Only parse request, call service, return response |
| Service functions | **20-100** | Can contain complex business logic, multiple queries |
| Model methods | **0-5** | Minimal, mostly properties or simple getters |

### ❌ Red Flags (Signs of Wrong Layer)

```python
# ❌ In routers/auth.py:
db.query(Employee).filter(Employee.email == email)  # DB query in router!!!
if user.role != "admin": ...                         # Business logic in router!!!

# ❌ In services/stories.py:
from fastapi import HTTPException  # FastAPI in service (ok for exceptions)
@app.get("/stories")              # FastAPI decorator in service!!!

# ❌ In models/employee.py:
def get_active_users(db):          # Method with DB connection!!!
    return db.query(Employee).filter(...)
```

### ✅ Correct Pattern

```python
# ✓ In routers/auth.py (5 lines):
@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_user(payload.email, payload.password, db)

# ✓ In services/auth_service.py (20+ lines, all business logic):
def login_user(email: str, password: str, db: Session):
    user = db.query(Employee).filter(Employee.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid")
    if user.status != "Active":
        raise HTTPException(status_code=403, detail="Not activated")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# ✓ In models/employee.py (ORM only):
class Employee(Base):
    __tablename__ = "employees"
    employee_id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    # NO methods, NO queries
```

---

## 🔄 Import Rules (Prevent Circular Dependencies)

```
Routers can import from:     ✅ services/  |  ✅ schemas  |  ✅ db/
                            ❌ models/    |  ❌ other routers

Services can import from:    ✅ models/    |  ✅ db/      |  ✅ schemas
                            ❌ routers/   |  ❌ other services (OK for utils)

Models can import from:      ✅ db.session  (Base only)
                            ❌ services   |  ❌ routers   |  ❌ other models

db/ can import from:         ✅ dotenv  |  ✅ sqlalchemy only
                            ❌ anything else
```

---

## 🛠️ File Organization Examples

### Before: Complex Mixed Concerns
```python
# backend/routers/stories.py (200 lines - TOO MUCH)
@router.get("/")
def get_stories(page: int, db: Session, user = Depends(get_current_user)):
    limit, offset = paginate(page)
    query = db.query(SuccessStory).filter(...)  # ❌ DB query here!
    if search:
        query = query.join(...).filter(...)     # ❌ Complex query!
    if sort_by == "recent":
        query = query.order_by(...)             # ❌ Business logic here!
    total = query.count()
    stories = query.all()
    return {                                     # ✓ Response only
        "stories": stories,
        "total": total,
        "page": page
    }
```

### After: Clean Separation
```python
# backend/routers/stories.py (3 lines - PERFECT)
@router.get("/")
def get_stories(page: int = 1, db: Session = Depends(get_db)):
    return stories_service.get_published_stories(page, db)

# backend/services/stories_service.py (50 lines - ALL logic here)
def get_published_stories(page: int, db: Session) -> dict:
    limit, offset = paginate(page)
    query = db.query(SuccessStory).filter(SuccessStory.status == "Posted")
    # ... sorting, filtering, pagination logic ...
    total = query.count()
    stories = query.offset(offset).limit(limit).all()
    return {
        "stories": [story_to_dict(s) for s in stories],
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }
```

---

## 📊 File Count After Refactoring

| Folder | Before | After | Notes |
|--------|--------|-------|-------|
| `routers/` | 5 files | 5 files | Cleaner (logic removed) |
| `services/` | 0 files | 5 files | NEW: All business logic |
| `models/` | 1 file (model.py) | 4 files | Organized by entity |
| `controllers/` | 5 files | ❌ DELETED | Logic moved to services |
| `db/` | 1 file (database.py) | ✨ NEW: 2 files | Reorganized & renamed |
| **Total** | **17 files** | **21 files** | Better organized |

---

## ✨ Layer Checklist

Use this when verifying each layer is correct:

### ✅ Routers (backend/routers/*.py)
- [ ] Functions are ≤ 10 lines
- [ ] No `db.query()` calls
- [ ] No business logic beyond schema validation
- [ ] All imports from (services, schemas, db.session)
- [ ] Error handling for HTTP responses

### ✅ Services (backend/services/*.py)
- [ ] All `db.query()` calls here
- [ ] All business logic here
- [ ] Type hints on all functions
- [ ] HTTPException for errors
- [ ] No FastAPI decorators
- [ ] Stateless (no instance variables)

### ✅ Models (backend/models/*.py)
- [ ] Only Column, ForeignKey, relationship definitions
- [ ] No methods (except properties if absolutely needed)
- [ ] No imports from services or routers
- [ ] Proper table names and constraints

### ✅ DB (backend/db/session.py)
- [ ] Only engine, SessionLocal, Base, get_db()
- [ ] No business logic
- [ ] No model definitions
- [ ] Clean configuration

---

**When in doubt, ask with `/refactoring-enforcer` agent!**
