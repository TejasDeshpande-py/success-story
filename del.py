from database import SessionLocal
from model import Employee, SuccessStory

db = SessionLocal()

db.query(SuccessStory).delete()
print("Deleted all stories")

db.query(Employee).delete()
print("Deleted all employees")

db.commit()
db.close()
print("Done!")