from fastapi import FastAPI
from routers import auth, stories, users, teams
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stories.router)
app.include_router(users.router)
app.include_router(teams.router)

app.mount("/static", StaticFiles(directory="static"), name="static")