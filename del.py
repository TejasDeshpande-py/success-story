from backend.database import SessionLocal
from backend.model import Employee, SuccessStory

db = SessionLocal()

db.query(SuccessStory).delete()
print("Deleted all stories")

db.query(Employee).delete()
print("Deleted all employees")

db.commit()
db.close()
print("Done!")