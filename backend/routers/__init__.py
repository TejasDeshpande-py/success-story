from backend.routers.auth import router as auth_router
from backend.routers.users import router as users_router
from backend.routers.teams import router as teams_router
from backend.routers.stories import router as stories_router
from backend.routers.banners import router as banners_router

__all__ = [
    "auth_router",
    "users_router",
    "teams_router",
    "stories_router",
    "banners_router",
]


