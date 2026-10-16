from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.schemas.website import WebsiteConnectionResult
from app.services.web_scraper import WebScrapeError, validate_public_url


class WordPressConnectionError(Exception):
    pass


def normalize_website_url(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise WordPressConnectionError("A website URL is required.")
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise WordPressConnectionError("Enter a valid http:// or https:// website URL.")
    if parsed.username or parsed.password:
        raise WordPressConnectionError("Website URLs cannot contain credentials.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") or "", "", ""))


def default_wordpress_api_url(website_url: str) -> str:
    return urljoin(f"{website_url.rstrip('/')}/", "wp-json/")


async def test_wordpress_connection(
    website_url: str,
    wordpress_api_url: str | None = None,
) -> WebsiteConnectionResult:
    checked_url = normalize_website_url(
        wordpress_api_url or default_wordpress_api_url(website_url)
    )
    try:
        url = await validate_public_url(checked_url)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=8.0),
            headers={"User-Agent": "OptiMind/0.1 (+WordPress connection test)"},
        ) as client:
            for _ in range(5):
                response = await client.get(url, follow_redirects=False)
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise WordPressConnectionError(
                            "The WordPress API returned an invalid redirect."
                        )
                    url = await validate_public_url(urljoin(url, location))
                    continue
                response.raise_for_status()
                break
            else:
                raise WordPressConnectionError("The WordPress API redirected too many times.")
    except WebScrapeError as exc:
        raise WordPressConnectionError(str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        return WebsiteConnectionResult(
            reachable=False,
            wordpress_detected=False,
            detail=f"The WordPress API returned HTTP {exc.response.status_code}.",
            checked_url=checked_url,
        )
    except httpx.HTTPError:
        return WebsiteConnectionResult(
            reachable=False,
            wordpress_detected=False,
            detail="The WordPress API could not be reached.",
            checked_url=checked_url,
        )

    try:
        payload = response.json()
    except ValueError:
        payload = None
    wordpress_detected = isinstance(payload, dict) and (
        "namespaces" in payload or "routes" in payload
    )
    return WebsiteConnectionResult(
        reachable=True,
        wordpress_detected=wordpress_detected,
        detail=(
            "WordPress REST API is available."
            if wordpress_detected
            else "The URL responded, but it does not look like a WordPress REST API."
        ),
        checked_url=url,
    )
