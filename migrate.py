from backend.db.session import engine, Base
from backend.models.employee import Employee
from backend.models.team import Team
from backend.models.story import SuccessStory, StoryComment, StoryReaction
from backend.models.banner import Banner

Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")