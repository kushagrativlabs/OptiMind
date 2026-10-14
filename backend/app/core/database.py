from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)


async def database_status() -> dict[str, str]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        return {"status": "offline", "detail": f"PostgreSQL unavailable: {type(exc).__name__}"}
    return {"status": "online", "detail": "PostgreSQL is responding"}


async def dispose_engine() -> None:
    await engine.dispose()

