from base64 import b64decode
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class ChatImage(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    media_type: str
    data: str = Field(min_length=1, max_length=7_000_000)

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        if value not in SUPPORTED_IMAGE_TYPES:
            raise ValueError("Images must be JPEG, PNG, or WebP.")
        return value

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: str) -> str:
        try:
            decoded = b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError("Image data must be valid base64.") from exc
        if len(decoded) > MAX_IMAGE_BYTES:
            raise ValueError("Each image must be 5 MB or smaller.")
        return value


class GenerationMetrics(BaseModel):
    duration_seconds: float = Field(ge=0)
    tokens_per_second: float | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class AgentActivity(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    tool: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=300)
    status: Literal["planned", "running", "completed", "failed"]
    detail: str = Field(default="", max_length=1_000)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)
    images: list[ChatImage] = Field(default_factory=list, max_length=3)
    metrics: GenerationMetrics | None = None
    activities: list[AgentActivity] = Field(default_factory=list, max_length=20)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    conversation_id: UUID | None = None
    web_search: bool = False


class OllamaChatResponse(BaseModel):
    message: ChatMessage
    model: str
    metrics: GenerationMetrics | None = None


class ChatResponse(OllamaChatResponse):
    conversation_id: UUID


class OllamaModel(BaseModel):
    name: str
    size: int = Field(ge=0)
    capabilities: list[str] = Field(default_factory=list)
