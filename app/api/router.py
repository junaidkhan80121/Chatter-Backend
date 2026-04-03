from fastapi import APIRouter
from app.api.v1 import auth, users, friends, conversations, files, notifications

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(friends.router)
api_router.include_router(conversations.router)
api_router.include_router(files.router)
api_router.include_router(notifications.router)
