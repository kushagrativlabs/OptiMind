import pytest

from app.schemas.auth import LoginRequest
from app.services.auth import hash_password, verify_password


def test_password_hash_round_trip() -> None:
    encoded = hash_password("a-strong-password-123")

    assert verify_password("a-strong-password-123", encoded)
    assert not verify_password("a-different-password", encoded)


def test_auth_request_normalizes_email() -> None:
    request = LoginRequest(email=" ADMIN@Example.com ", password="a-strong-password-123")

    assert request.email == "admin@example.com"


def test_passwords_must_be_long() -> None:
    with pytest.raises(ValueError):
        hash_password("short")
