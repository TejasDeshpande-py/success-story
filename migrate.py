from backend.database import engine
from backend.model import Base

Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")