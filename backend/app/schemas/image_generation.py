from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    conversation_id: UUID | None = None
    website_id: UUID | None = None
    conversation_model: str = Field(default="qwen2.5:3b", min_length=1, max_length=200)


class ImageGenerationResponse(BaseModel):
    message: ChatMessage
    conversation_id: UUID
    model: str
