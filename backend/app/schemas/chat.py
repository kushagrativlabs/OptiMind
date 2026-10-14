from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    conversation_id: UUID | None = None


class OllamaChatResponse(BaseModel):
    message: ChatMessage
    model: str


class ChatResponse(OllamaChatResponse):
    conversation_id: UUID


class OllamaModel(BaseModel):
    name: str
    size: int = Field(ge=0)
