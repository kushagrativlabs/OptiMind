import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session, session_factory
from app.models import Conversation, Message
from app.schemas.chat import ChatRequest, ChatResponse, OllamaModel
from app.services.ollama import OllamaConnectionError, OllamaModelError, OllamaService

router = APIRouter()


def stream_event(event_type: str, **data: object) -> str:
    return json.dumps({"type": event_type, **data}) + "\n"


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


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    service = OllamaService()
    model = request.model or service.model
    latest_user_message = next(
        (message for message in reversed(request.messages) if message.role == "user"),
        None,
    )
    if latest_user_message is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user message is required.",
        )

    try:
        await service.validate_model(model)
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
    await session.commit()
    conversation_id = conversation.id

    async def generate() -> AsyncIterator[str]:
        chunks: list[str] = []
        yield stream_event(
            "meta", conversation_id=str(conversation_id), model=model
        )
        try:
            async for chunk in service.chat_stream(request.messages, model):
                chunks.append(chunk)
                yield stream_event("token", content=chunk)

            content = "".join(chunks).strip()
            if not content:
                raise OllamaConnectionError("Ollama returned an empty response.")

            async with session_factory() as save_session:
                saved_conversation = await save_session.get(Conversation, conversation_id)
                save_session.add(
                    Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=content,
                    )
                )
                if saved_conversation is not None:
                    saved_conversation.updated_at = datetime.now(UTC)
                await save_session.commit()
            yield stream_event("done")
        except OllamaConnectionError as exc:
            yield stream_event("error", detail=str(exc))

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
