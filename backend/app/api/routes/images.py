from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models import Conversation, Message
from app.schemas.chat import ChatMessage
from app.schemas.image_generation import ImageGenerationRequest, ImageGenerationResponse
from app.services.image_generation import ImageGenerationError, image_generation_service

router = APIRouter(prefix="/images")


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    session: AsyncSession = Depends(get_session),
) -> ImageGenerationResponse:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An image prompt is required.",
        )

    try:
        image = await image_generation_service.generate(prompt)
    except ImageGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if request.conversation_id is None:
        conversation = Conversation(
            title=f"Image: {' '.join(prompt.split())[:72]}",
            model=request.conversation_model,
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
        conversation.updated_at = datetime.now(UTC)

    session.add_all(
        [
            Message(
                conversation_id=conversation.id,
                role="user",
                content=prompt,
                images=[],
            ),
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=f"Generated locally with {settings.image_generation_model}.",
                images=[image.model_dump()],
            ),
        ]
    )
    await session.commit()
    return ImageGenerationResponse(
        message=ChatMessage(
            role="assistant",
            content=f"Generated locally with {settings.image_generation_model}.",
            images=[image],
        ),
        conversation_id=conversation.id,
        model=settings.image_generation_model,
    )
