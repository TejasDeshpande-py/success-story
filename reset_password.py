# reset_passwords.py
from database import SessionLocal
from model import Employee
from security import hash_password

db = SessionLocal()

updates = {
    "asha.hr@example.com":   "asha123",    # HR
    "ravi.dev@example.com":  "ravi123",    # Non-HR
    "sara.dev@example.com":  "sara123",    # Non-HR
    "tejas.dev@example.com": "tejas123",   # Non-HR
}

for email, plain_password in updates.items():
    user = db.query(Employee).filter(Employee.email == email).first()
    if user:
        user.password_hash = hash_password(plain_password)
        print(f" Reset password for {email} → {plain_password}")
    else:
        print(f"Not found: {email}")

db.commit()
db.close()