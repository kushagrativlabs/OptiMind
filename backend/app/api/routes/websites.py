from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Website
from app.schemas.website import (
    WebsiteConnectionResult,
    WebsiteCreate,
    WebsiteResponse,
    WebsiteUpdate,
)
from app.services.wordpress import (
    WordPressConnectionError,
    default_wordpress_api_url,
    normalize_website_url,
    test_wordpress_connection,
)

router = APIRouter(prefix="/websites")


def clean_name(value: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise HTTPException(status_code=400, detail="A website name is required.")
    return name


def clean_url(value: str) -> str:
    try:
        return normalize_website_url(value)
    except WordPressConnectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[WebsiteResponse])
async def list_websites(
    session: AsyncSession = Depends(get_session),
) -> list[Website]:
    result = await session.scalars(select(Website).order_by(Website.name.asc()))
    return list(result)


@router.post("", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
async def create_website(
    request: WebsiteCreate,
    session: AsyncSession = Depends(get_session),
) -> Website:
    url = clean_url(request.url)
    website = Website(
        name=clean_name(request.name),
        url=url,
        wordpress_api_url=(
            clean_url(request.wordpress_api_url)
            if request.wordpress_api_url
            else default_wordpress_api_url(url)
        ),
        model=request.model.strip(),
    )
    session.add(website)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="That website is already added.") from exc
    await session.refresh(website)
    return website


@router.patch("/{website_id}", response_model=WebsiteResponse)
async def update_website(
    website_id: UUID,
    request: WebsiteUpdate,
    session: AsyncSession = Depends(get_session),
) -> Website:
    website = await session.get(Website, website_id)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found.")
    if request.name is not None:
        website.name = clean_name(request.name)
    if request.url is not None:
        website.url = clean_url(request.url)
    if request.wordpress_api_url is not None:
        website.wordpress_api_url = (
            clean_url(request.wordpress_api_url)
            if request.wordpress_api_url
            else default_wordpress_api_url(website.url)
        )
    if request.model is not None:
        website.model = request.model.strip()
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="That website URL is already used.") from exc
    await session.refresh(website)
    return website


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website(
    website_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    website = await session.get(Website, website_id)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found.")
    await session.delete(website)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{website_id}/test", response_model=WebsiteConnectionResult)
async def test_website_connection(
    website_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WebsiteConnectionResult:
    website = await session.get(Website, website_id)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found.")
    try:
        return await test_wordpress_connection(website.url, website.wordpress_api_url)
    except WordPressConnectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
