from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Conversation, Message
from app.schemas.conversation import ConversationDetail, ConversationSummary

router = APIRouter(prefix="/conversations")


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    session: AsyncSession = Depends(get_session),
) -> list[Conversation]:
    result = await session.scalars(
        select(Conversation).order_by(Conversation.updated_at.desc()).limit(100)
    )
    return list(result)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    result = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        model=conversation.model,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=list(result),
    )
