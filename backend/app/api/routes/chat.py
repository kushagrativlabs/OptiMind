from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Conversation, Message
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
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    model = request.model or OllamaService().model
    latest_user_message = next(
        (message for message in reversed(request.messages) if message.role == "user"),
        None,
    )
    if latest_user_message is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user message is required.",
        )

    if request.conversation_id is None:
        title = " ".join(latest_user_message.content.split())[:80] or "New conversation"
        conversation = Conversation(title=title, model=model)
        session.add(conversation)
        await session.flush()
    else:
        conversation = await session.get(Conversation, request.conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        conversation.model = model
        conversation.updated_at = datetime.now(UTC)

    session.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=latest_user_message.content,
        )
    )
    await session.flush()

    try:
        response = await OllamaService().chat(request.messages, model)
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

    session.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response.message.content,
        )
    )
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    return ChatResponse(
        message=response.message,
        model=response.model,
        conversation_id=conversation.id,
    )
