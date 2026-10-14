from fastapi import APIRouter

from app.api.routes import chat, conversations, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(conversations.router, tags=["conversations"])
