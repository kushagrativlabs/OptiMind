from urllib.parse import urljoin

import httpx

from app.core.config import settings
from app.services.web_scraper import (
    MAX_SITE_PAGES,
    WebPage,
    WebScrapeError,
    inspect_page_data,
    validate_public_url,
    web_scraper,
)


class WordPressPagesError(Exception):
    pass


async def fetch_wordpress_pages(api_url: str, website_url: str) -> list[WebPage]:
    """Fetch published pages through the WordPress REST API, read-only."""
    base = await validate_public_url(api_url.rstrip("/") + "/")
    auth = None
    if settings.wordpress_username and settings.wordpress_app_password:
        auth = (settings.wordpress_username, settings.wordpress_app_password)

    pages: list[WebPage] = []
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=8.0),
            headers={"User-Agent": "OptiMind/0.1 (+WordPress REST reader)"},
            auth=auth,
        ) as client:
            for page_number in range(1, 100):
                response = await client.get(
                    urljoin(base, "wp/v2/pages"),
                    params={
                        "per_page": min(100, MAX_SITE_PAGES),
                        "page": page_number,
                        "status": "publish",
                        "orderby": "date",
                        "order": "asc",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list) or not payload:
                    break
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    link = str(item.get("link") or website_url)
                    title = str((item.get("title") or {}).get("rendered") or "")
                    rendered = str((item.get("content") or {}).get("rendered") or "")
                    if not rendered:
                        continue
                    parsed_title, text, links, seo = inspect_page_data(
                        f"<title>{title}</title>{rendered}", link
                    )
                    # The API is authoritative for page discovery/content. Read the
                    # public page as well so title/meta/canonical/schema/image facts
                    # come from the rendered document for this exact URL.
                    try:
                        rendered_page = await web_scraper.scrape(link)
                        seo = rendered_page.seo or seo
                        links = rendered_page.links or links
                    except WebScrapeError:
                        pass
                    pages.append(
                        WebPage(
                            url=link,
                            title=title or parsed_title,
                            text=text,
                            links=links,
                            seo=seo,
                        )
                    )
                    if len(pages) >= MAX_SITE_PAGES:
                        return pages
                total_pages = int(response.headers.get("X-WP-TotalPages", page_number))
                if page_number >= total_pages:
                    break
    except WebScrapeError as exc:
        raise WordPressPagesError(str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise WordPressPagesError(
                "WordPress API authentication failed. Check the backend Application Password."
            ) from exc
        raise WordPressPagesError(
            f"WordPress pages API returned HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise WordPressPagesError("Could not read pages from the WordPress REST API.") from exc

    if not pages:
        raise WordPressPagesError("The WordPress REST API returned no published pages.")
    return pages
