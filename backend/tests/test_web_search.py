import httpx
import pytest

from app.services.web_search import WebSearchError, WebSearchService


@pytest.mark.asyncio
async def test_web_search_reports_missing_configuration() -> None:
    service = WebSearchService(enabled=False)

    assert (await service.status())["status"] == "offline"


@pytest.mark.asyncio
async def test_web_search_returns_normalized_results() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Official release notes",
                        "url": "https://example.com/releases",
                        "content": "Current release information",
                    }
                ]
            },
        )

    service = WebSearchService(
        base_url="http://search.test",
        enabled=True,
        transport=httpx.MockTransport(handler),
    )
    results = await service.search(" latest release ")

    assert results[0].title == "Official release notes"
    assert results[0].url == "https://example.com/releases"


@pytest.mark.asyncio
async def test_web_search_reports_an_unavailable_instance() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    service = WebSearchService(
        base_url="http://search.test",
        enabled=True,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(WebSearchError, match="HTTP 503"):
        await service.search("latest release")
