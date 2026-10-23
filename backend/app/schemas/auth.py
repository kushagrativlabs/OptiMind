from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_email(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("Enter a valid email address.")
    return normalized


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=12)

    _normalize_email = field_validator("email")(validate_email)


class UserCreate(BaseModel):
    email: str
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12)

    _normalize_email = field_validator("email")(validate_email)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse
