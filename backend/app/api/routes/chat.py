import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import AgentToolError, ToolResult, agent_tools
from app.core.database import get_session, session_factory
from app.models import Conversation, Message, Website
from app.schemas.chat import AgentActivity, ChatRequest, ChatResponse, OllamaModel
from app.services.ollama import (
    OllamaConnectionError,
    OllamaModelError,
    OllamaService,
    generation_metrics,
)

router = APIRouter()


def stream_event(event_type: str, **data: object) -> str:
    return json.dumps({"type": event_type, **data}) + "\n"


async def execute_tools(
    request: ChatRequest,
    active_website_url: str | None = None,
) -> tuple[list[ToolResult], list[AgentActivity]]:
    results: list[ToolResult] = []
    activities: list[AgentActivity] = []
    for call in agent_tools.plan(
        request.messages,
        request.web_search,
        active_website_url,
    ):
        try:
            result = await agent_tools.execute(call)
        except AgentToolError as exc:
            activities.append(call.activity("failed", str(exc)))
            raise
        results.append(result)
        activities.append(call.activity("completed", result.detail))
    return results, activities


async def load_website(
    website_id: object | None,
    session: AsyncSession,
) -> Website | None:
    if website_id is None:
        return None
    website = await session.get(Website, website_id)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found.")
    return website


def website_prompt_context(website: Website | None) -> str | None:
    if website is None:
        return None
    return (
        f"Name: {website.name}\n"
        f"Website URL: {website.url}\n"
        f"WordPress REST API: {website.wordpress_api_url or 'Not configured'}\n"
        f"Preferred model: {website.model}"
    )


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

    if request.conversation_id is None:
        website = await load_website(request.website_id, session)
        if request.model is None and website is not None:
            model = website.model
        title = " ".join(latest_user_message.content.split())[:80] or "New conversation"
        conversation = Conversation(
            title=title,
            model=model,
            website_id=website.id if website else None,
        )
        session.add(conversation)
        await session.flush()
    else:
        conversation = await session.get(Conversation, request.conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        website = await load_website(
            request.website_id or conversation.website_id,
            session,
        )
        if request.website_id is not None:
            conversation.website_id = request.website_id
        if request.model is None and website is not None:
            model = website.model
        conversation.model = model
        conversation.updated_at = datetime.now(UTC)

    session.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=latest_user_message.content,
            images=[image.model_dump() for image in latest_user_message.images],
        )
    )
    await session.flush()

    try:
        tool_results, activities = await execute_tools(
            request,
            website.url if website else None,
        )
        response = await service.chat(
            request.messages,
            model,
            use_web_search=request.web_search,
            tool_results=tool_results,
            website_context=website_prompt_context(website),
        )
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
    except AgentToolError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    response_message = response.message.model_copy(update={"activities": activities})

    session.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_message.content,
            images=[],
            metrics=(response.metrics.model_dump() if response.metrics else None),
            activities=[activity.model_dump() for activity in activities],
        )
    )
    conversation.updated_at = datetime.now(UTC)
    await session.commit()
    return ChatResponse(
        message=response_message,
        model=response.model,
        conversation_id=conversation.id,
        metrics=response.metrics,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
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
        await service.validate_model(
            model,
            require_vision=any(message.images for message in request.messages),
        )
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
        website = await load_website(request.website_id, session)
        if request.model is None and website is not None:
            model = website.model
        title = " ".join(latest_user_message.content.split())[:80] or "New conversation"
        conversation = Conversation(
            title=title,
            model=model,
            website_id=website.id if website else None,
        )
        session.add(conversation)
        await session.flush()
    else:
        conversation = await session.get(Conversation, request.conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        website = await load_website(
            request.website_id or conversation.website_id,
            session,
        )
        if request.website_id is not None:
            conversation.website_id = request.website_id
        if request.model is None and website is not None:
            model = website.model
        conversation.model = model
        conversation.updated_at = datetime.now(UTC)

    session.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=latest_user_message.content,
            images=[image.model_dump() for image in latest_user_message.images],
        )
    )
    await session.commit()
    conversation_id = conversation.id

    async def generate() -> AsyncIterator[str]:
        chunks: list[str] = []
        metrics = None
        activities: list[AgentActivity] = []
        tool_results: list[ToolResult] = []
        yield stream_event(
            "meta", conversation_id=str(conversation_id), model=model
        )
        try:
            if await http_request.is_disconnected():
                return
            calls = agent_tools.plan(
                request.messages,
                request.web_search,
                website.url if website else None,
            )
            for call in calls:
                if await http_request.is_disconnected():
                    return
                planned = call.activity("planned")
                activities.append(planned)
                yield stream_event("activity", activity=planned.model_dump())

            for call in calls:
                if await http_request.is_disconnected():
                    return
                running = call.activity("running")
                activities = [
                    running if activity.id == call.id else activity
                    for activity in activities
                ]
                yield stream_event("activity", activity=running.model_dump())
                try:
                    result = await agent_tools.execute(call)
                except AgentToolError as exc:
                    failed = call.activity("failed", str(exc))
                    activities = [
                        failed if activity.id == call.id else activity
                        for activity in activities
                    ]
                    yield stream_event("activity", activity=failed.model_dump())
                    raise OllamaConnectionError(str(exc)) from exc
                tool_results.append(result)
                completed = call.activity("completed", result.detail)
                activities = [
                    completed if activity.id == call.id else activity
                    for activity in activities
                ]
                yield stream_event("activity", activity=completed.model_dump())

            if await http_request.is_disconnected():
                return
            async for event in service.chat_stream(
                request.messages,
                model,
                use_web_search=request.web_search,
                tool_results=tool_results,
                website_context=website_prompt_context(website),
            ):
                if event.content:
                    chunks.append(event.content)
                    yield stream_event("token", content=event.content)
                if event.done:
                    metrics = generation_metrics(
                        {
                            "eval_count": event.eval_count,
                            "eval_duration": event.eval_duration,
                            "total_duration": event.total_duration,
                        }
                    )

            content = service.with_verified_page_audit("".join(chunks).strip(), tool_results)
            if not content:
                raise OllamaConnectionError("Ollama returned an empty response.")

            async with session_factory() as save_session:
                saved_conversation = await save_session.get(Conversation, conversation_id)
                save_session.add(
                    Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=content,
                        images=[],
                        metrics=(metrics.model_dump() if metrics else None),
                        activities=[activity.model_dump() for activity in activities],
                    )
                )
                if saved_conversation is not None:
                    saved_conversation.updated_at = datetime.now(UTC)
                await save_session.commit()
            yield stream_event(
                "done",
                metrics=(metrics.model_dump() if metrics else None),
            )
        except OllamaConnectionError as exc:
            yield stream_event("error", detail=str(exc))

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
