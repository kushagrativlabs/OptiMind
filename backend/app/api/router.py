from fastapi import APIRouter

from app.api.routes import chat, conversations, health, images

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(images.router, tags=["images"])
api_router.include_router(conversations.router, tags=["conversations"])
