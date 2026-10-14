from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=200)


class ChatResponse(BaseModel):
    message: ChatMessage
    model: str


class OllamaModel(BaseModel):
    name: str
    size: int = Field(ge=0)

