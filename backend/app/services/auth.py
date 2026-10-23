import base64
import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session, session_factory
from app.models.user import AuthToken, User

_ITERATIONS = 600_000
_bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Passwords must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    salt_text = base64.urlsafe_b64encode(salt).decode()
    digest_text = base64.urlsafe_b64encode(digest).decode()
    return f"pbkdf2_sha256${_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            base64.urlsafe_b64decode(salt.encode()),
            int(iterations),
        )
        return hmac.compare_digest(
            base64.urlsafe_b64encode(digest).decode(), expected
        )
    except (TypeError, ValueError):
        return False


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def authenticate_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    result = await session.scalars(
        select(User)
        .join(AuthToken, AuthToken.user_id == User.id)
        .where(
            AuthToken.token_hash == _token_digest(credentials.credentials),
            AuthToken.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )
    user = result.first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return user


async def require_admin(user: User = Depends(authenticate_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


async def create_token(session: AsyncSession, user: User) -> tuple[str, datetime]:
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.auth_token_ttl_minutes)
    session.add(
        AuthToken(
            user_id=user.id,
            token_hash=_token_digest(raw_token),
            expires_at=expires_at,
        )
    )
    return raw_token, expires_at


async def ensure_initial_admin() -> None:
    if (
        not settings.admin_email
        or not settings.admin_password
        or settings.admin_password.startswith("replace-with-")
    ):
        return
    try:
        async with session_factory() as session:
            admin_email = settings.admin_email.lower()
            result = await session.scalar(select(User).where(User.email == admin_email))
            if result is None:
                session.add(
                    User(
                        email=settings.admin_email.lower(),
                        full_name="OptiMind Admin",
                        password_hash=hash_password(settings.admin_password),
                        role="admin",
                    )
                )
                await session.commit()
    except Exception as exc:  # The API can still start while migrations/database are unavailable.
        logger.warning("Initial admin was not provisioned: %s", type(exc).__name__)
