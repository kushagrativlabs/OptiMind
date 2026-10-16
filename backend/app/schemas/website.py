from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebsiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2_000)
    wordpress_api_url: str | None = Field(default=None, max_length=2_000)
    model: str = Field(min_length=1, max_length=200)


class WebsiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = Field(default=None, min_length=1, max_length=2_000)
    wordpress_api_url: str | None = Field(default=None, max_length=2_000)
    model: str | None = Field(default=None, min_length=1, max_length=200)


class WebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    wordpress_api_url: str | None
    model: str
    created_at: datetime
    updated_at: datetime


class WebsiteConnectionResult(BaseModel):
    reachable: bool
    wordpress_detected: bool
    detail: str
    checked_url: str
