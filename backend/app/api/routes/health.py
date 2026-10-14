from fastapi import APIRouter

from app.core.config import settings
from app.core.database import database_status
from app.services.ollama import OllamaService

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "online"}


@router.get("/status")
async def status() -> dict[str, object]:
    database = await database_status()
    ollama = await OllamaService().status()
    return {
        "api": {"status": "online", "detail": "FastAPI is responding"},
        "database": database,
        "ollama": {**ollama, "model": settings.ollama_model},
    }
