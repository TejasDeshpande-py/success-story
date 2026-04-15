from backend.db.session import SessionLocal
from backend.models.employee import Employee
from backend.auth.security import hash_password
from dotenv import load_dotenv
import os

load_dotenv()

db = SessionLocal()

existing = db.query(Employee).filter(Employee.role_id == 2).first()
if existing:
    print("Admin already exists!")
else:
    admin = Employee(
        name="Super Admin",
        email=os.getenv("ADMIN_EMAIL"),
        password_hash=hash_password(os.getenv("ADMIN_PASSWORD")),
        picture="https://randomuser.me/api/portraits/men/1.jpg",
        tricon_id="TRI000",
        role_id=2,
        team_id=None,
        status="Active",
    )
    db.add(admin)
    db.commit()
    print("Admin created successfully!")

db.close()