from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserCreate, UserResponse
from app.services.auth import (
    authenticate_user,
    create_token,
    hash_password,
    require_admin,
    verify_password,
)

router = APIRouter(prefix="/auth")
users_router = APIRouter(prefix="/users")


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> LoginResponse:
    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    token, expires_at = await create_token(session, user)
    await session.commit()
    return LoginResponse(access_token=token, expires_at=expires_at, user=user)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(authenticate_user)) -> User:
    return user


@users_router.get("", response_model=list[UserResponse])
async def list_users(
    _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> list[User]:
    return list(await session.scalars(select(User).order_by(User.created_at.asc())))


@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role="member",
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from exc
    await session.refresh(user)
    return user
