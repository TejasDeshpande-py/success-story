from fastapi import FastAPI
from routers import auth, stories, users, teams

app = FastAPI()

app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(users.router)
app.include_router(teams.router)