from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.chat import ChatMessage


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    model: str
    website_id: UUID | None
    created_at: datetime
    updated_at: datetime


class StoredMessage(ChatMessage):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage]
