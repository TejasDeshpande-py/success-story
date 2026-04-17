from backend.db import SessionLocal
from backend.models import Employee, SuccessStory

db = SessionLocal()

db.query(SuccessStory).delete()
print("Deleted all stories")

db.query(Employee).delete()
print("Deleted all employees")

db.commit()
db.close()
print("Done!")