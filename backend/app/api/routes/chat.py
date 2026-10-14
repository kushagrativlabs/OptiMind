from fastapi import APIRouter, HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse, OllamaModel
from app.services.ollama import OllamaConnectionError, OllamaModelError, OllamaService

router = APIRouter()


@router.get("/models", response_model=list[OllamaModel])
async def models() -> list[OllamaModel]:
    try:
        return await OllamaService().models()
    except OllamaConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await OllamaService().chat(request.messages, request.model)
    except OllamaModelError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except OllamaConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

