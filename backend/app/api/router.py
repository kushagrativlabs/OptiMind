from fastapi import APIRouter

from app.api.routes import auth, chat, conversations, health, images, websites

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(images.router, tags=["images"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(websites.router, tags=["websites"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(auth.users_router, tags=["users"])
