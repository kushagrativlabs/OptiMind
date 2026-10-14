from dataclasses import dataclass

import httpx

from app.core.config import settings

MAX_SEARCH_RESULTS = 5


class WebSearchError(Exception):
    pass


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    content: str


class WebSearchService:
    def __init__(
        self,
        base_url: str | None = None,
        enabled: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.searxng_base_url).rstrip("/")
        self.enabled = settings.web_search_enabled if enabled is None else enabled
        self.transport = transport

    async def status(self) -> dict[str, str]:
        if not self.enabled:
            return {
                "status": "offline",
                "detail": "Web search is disabled in the environment configuration",
            }
        try:
            async with httpx.AsyncClient(timeout=3.0, transport=self.transport) as client:
                response = await client.get(f"{self.base_url}/")
                response.raise_for_status()
        except httpx.HTTPError:
            return {
                "status": "offline",
                "detail": "SearXNG is not responding. Run: npm run web-search:setup",
            }
        return {
            "status": "online",
            "detail": "Free local SearXNG web search is ready",
        }

    async def search(self, query: str) -> list[WebSearchResult]:
        if not self.enabled:
            raise WebSearchError(
                "Web search is disabled. Set WEB_SEARCH_ENABLED=true in .env."
            )

        normalized_query = " ".join(query.split())[:500]
        if not normalized_query:
            raise WebSearchError("A search query is required.")

        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    data={
                        "q": normalized_query,
                        "format": "json",
                        "categories": "general",
                        "language": "auto",
                        "safesearch": "1",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                detail = "The search engines temporarily rate-limited SearXNG."
            else:
                detail = f"SearXNG returned HTTP {exc.response.status_code}."
            raise WebSearchError(detail) from exc
        except httpx.HTTPError as exc:
            raise WebSearchError(
                "SearXNG is unavailable. Run: npm run web-search:setup"
            ) from exc

        results: list[WebSearchResult] = []
        for item in response.json().get("results", []):
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            content = str(item.get("content", "")).strip()
            if title and url:
                results.append(WebSearchResult(title=title, url=url, content=content))
            if len(results) == MAX_SEARCH_RESULTS:
                break

        if not results:
            raise WebSearchError("Web search returned no results for that question.")
        return results


web_search_service = WebSearchService()
