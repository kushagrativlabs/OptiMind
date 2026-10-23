from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine
from app.services.auth import ensure_initial_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_initial_admin()
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    description="Local-first AI workspace for website growth.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs"}
