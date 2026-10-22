import asyncio
import ipaddress
import json
import os
import re
import socket
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

import httpx

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
BARE_DOMAIN_PATTERN = re.compile(
    r"(?<![@\w])(?:www\.)?[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*"
    r"\.(?:com|org|net|io|ai|co|dev|app|info|biz|me|in|uk|us|ca|au|de|fr|jp|site|online|xyz|tech)"
    r"(?::\d{1,5})?(?:/[^\s<>\"']*)?",
    re.IGNORECASE,
)
SKIPPED_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}
SKIPPED_EXTENSIONS = {
    ".7z",
    ".avi",
    ".css",
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".rar",
    ".svg",
    ".tar",
    ".webp",
    ".xml",
    ".zip",
}
MAX_DOWNLOAD_BYTES = 2_000_000
MAX_PAGE_CHARACTERS = 12_000
MAX_INPUT_URLS = 2
# A hard safety ceiling prevents an accidental crawl from exhausting local
# resources, while allowing normal websites to be crawled beyond the old
# eight-page/two-level sample.
MAX_SITE_PAGES = max(8, int(os.getenv("OPTIMIND_MAX_SITE_PAGES", "100")))
MAX_CRAWL_DEPTH = max(2, int(os.getenv("OPTIMIND_MAX_CRAWL_DEPTH", "6")))
CACHE_SECONDS = 600


class WebScrapeError(Exception):
    pass


@dataclass(frozen=True)
class PageSEO:
    meta_description: str | None = None
    canonical_url: str | None = None
    robots: str | None = None
    headings: tuple[tuple[str, str], ...] = ()
    schema_types: tuple[str, ...] = ()
    image_count: int = 0
    images_missing_alt: int = 0
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class WebPage:
    url: str
    title: str
    text: str
    links: tuple[str, ...] = ()
    seo: PageSEO | None = None
    response_time_ms: int | None = None
    response_bytes: int | None = None
    lighthouse: dict[str, object] | None = None


class ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.links: list[str] = []
        self.skipped_depth = 0
        self.in_title = False
        self.in_json_ld = False
        self.json_ld_parts: list[str] = []
        self.json_ld_documents: list[str] = []
        self.meta_description: str | None = None
        self.canonical_href: str | None = None
        self.robots: str | None = None
        self.current_heading: str | None = None
        self.heading_parts: list[str] = []
        self.headings: list[tuple[str, str]] = []
        self.image_count = 0
        self.images_missing_alt = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {name.lower(): value for name, value in attrs}
        if tag == "script" and (attributes.get("type") or "").lower() == (
            "application/ld+json"
        ):
            self.in_json_ld = True
            self.json_ld_parts = []
        elif tag in SKIPPED_TAGS:
            self.skipped_depth += 1
        elif tag == "a" and self.skipped_depth == 0:
            href = attributes.get("href")
            if href:
                self.links.append(href)
        elif tag == "meta" and self.skipped_depth == 0:
            name = (attributes.get("name") or "").lower()
            content = (attributes.get("content") or "").strip()
            if name == "description" and content:
                self.meta_description = content
            elif name == "robots" and content:
                self.robots = content
        elif tag == "link" and self.skipped_depth == 0:
            rel = (attributes.get("rel") or "").lower().split()
            if "canonical" in rel and attributes.get("href"):
                self.canonical_href = attributes["href"]
        elif tag == "img" and self.skipped_depth == 0:
            self.image_count += 1
            if not (attributes.get("alt") or "").strip():
                self.images_missing_alt += 1
        elif tag == "title" and self.skipped_depth == 0:
            self.in_title = True
        elif tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "article", "section"}:
            self.parts.append("\n")
            if tag in {"h1", "h2", "h3", "h4"}:
                self.current_heading = tag
                self.heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self.in_json_ld:
            document = "".join(self.json_ld_parts).strip()
            if document:
                self.json_ld_documents.append(document)
            self.in_json_ld = False
            self.json_ld_parts = []
        elif tag in SKIPPED_TAGS and self.skipped_depth:
            self.skipped_depth -= 1
        elif tag == "title":
            self.in_title = False
        elif tag == self.current_heading:
            value = " ".join(" ".join(self.heading_parts).split())
            if value:
                self.headings.append((tag, value))
            self.current_heading = None
            self.heading_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_json_ld:
            self.json_ld_parts.append(data)
            return
        if self.skipped_depth or not data.strip():
            return
        if self.in_title:
            self.title_parts.append(data)
        else:
            self.parts.append(data)
            if self.current_heading:
                self.heading_parts.append(data)

    def result(self) -> tuple[str, str]:
        title = " ".join(" ".join(self.title_parts).split())
        text = re.sub(r"\n\s*\n+", "\n", "".join(self.parts))
        text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
        return title, text

    def seo_result(self, base_url: str) -> PageSEO:
        schema_types: set[str] = set()

        def collect_types(value: object) -> None:
            if isinstance(value, dict):
                item_type = value.get("@type")
                if isinstance(item_type, str):
                    schema_types.add(item_type)
                elif isinstance(item_type, list):
                    schema_types.update(str(item) for item in item_type if item)
                for child in value.values():
                    collect_types(child)
            elif isinstance(value, list):
                for child in value:
                    collect_types(child)

        for document in self.json_ld_documents:
            try:
                collect_types(json.loads(document))
            except (TypeError, ValueError):
                continue

        canonical_url = urljoin(base_url, self.canonical_href) if self.canonical_href else None
        h1_count = sum(1 for level, _ in self.headings if level == "h1")
        quality_flags: list[str] = []
        if h1_count == 0:
            quality_flags.append("No H1 heading detected")
        elif h1_count > 1:
            quality_flags.append(f"Multiple H1 headings detected ({h1_count})")
        if re.search(r"_{3,}|\.{3,}|\bplaceholder\b|\bexample phone\b", "".join(self.parts), re.I):
            quality_flags.append("Possible placeholder text detected")
        return PageSEO(
            meta_description=self.meta_description,
            canonical_url=canonical_url,
            robots=self.robots,
            headings=tuple(self.headings),
            schema_types=tuple(sorted(schema_types)),
            image_count=self.image_count,
            images_missing_alt=self.images_missing_alt,
            quality_flags=tuple(quality_flags),
        )


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    explicit_spans: list[tuple[int, int]] = []
    for match in URL_PATTERN.finditer(text):
        url = match.group().rstrip(".,;:!?)]}")
        if url not in urls:
            urls.append(url)
        explicit_spans.append(match.span())

    for match in BARE_DOMAIN_PATTERN.finditer(text):
        if any(start <= match.start() < end for start, end in explicit_spans):
            continue
        domain = match.group().rstrip(".,;:!?)]}")
        url = f"https://{domain}"
        if url not in urls:
            urls.append(url)
    return urls


def extract_readable_text(html: str) -> tuple[str, str]:
    parser = ReadableHTMLParser()
    parser.feed(html)
    return parser.result()


def extract_page_data(html: str, base_url: str) -> tuple[str, str, tuple[str, ...]]:
    title, text, links, _ = inspect_page_data(html, base_url)
    return title, text, links


def inspect_page_data(
    html: str,
    base_url: str,
) -> tuple[str, str, tuple[str, ...], PageSEO]:
    parser = ReadableHTMLParser()
    parser.feed(html)
    title, text = parser.result()
    links: list[str] = []
    for href in parser.links:
        absolute = urljoin(base_url, href)
        parsed = urlsplit(absolute)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        normalized = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))
        if normalized not in links:
            links.append(normalized)
    return title, text, tuple(links), parser.seo_result(base_url)


def _site_hostname(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").lower()
    return hostname.removeprefix("www.")


def _can_crawl(root_url: str, candidate_url: str) -> bool:
    parsed = urlsplit(candidate_url)
    if _site_hostname(candidate_url) != _site_hostname(root_url):
        return False
    path = parsed.path.lower().rstrip("/")
    return not any(path.endswith(extension) for extension in SKIPPED_EXTENSIONS)


def _page_key(url: str) -> str:
    """Return a stable identity for a page across slash/www variants."""
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    port = parsed.port
    netloc = hostname if port is None else f"{hostname}:{port}"
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


def _is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def validate_public_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise WebScrapeError("Only public http:// and https:// URLs are supported.")
    if parsed.username or parsed.password:
        raise WebScrapeError("URLs containing usernames or passwords are not supported.")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            parsed.hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except (OSError, ValueError) as exc:
        raise WebScrapeError(f"Could not resolve {parsed.hostname}.") from exc

    if not addresses or any(not _is_public_address(item[4][0]) for item in addresses):
        raise WebScrapeError("Private and local network URLs cannot be scraped.")

    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


class WebScraper:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, WebPage]] = {}

    async def scrape(self, requested_url: str) -> WebPage:
        cached = self._cache.get(requested_url)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1]

        url = await validate_public_url(requested_url)
        request_started = time.perf_counter()
        timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
        headers = {"User-Agent": "OptiMind/0.1 (+local website analysis)"}

        try:
            async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
                for _ in range(5):
                    async with client.stream("GET", url, follow_redirects=False) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise WebScrapeError("The website returned an invalid redirect.")
                            url = await validate_public_url(urljoin(url, location))
                            continue

                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if not any(
                            allowed in content_type
                            for allowed in ("text/html", "application/xhtml+xml", "text/plain")
                        ):
                            raise WebScrapeError(
                                "That URL is not an HTML or plain-text webpage."
                            )

                        chunks: list[bytes] = []
                        size = 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_DOWNLOAD_BYTES:
                                raise WebScrapeError("The webpage is too large to analyze safely.")
                            chunks.append(chunk)
                        raw = b"".join(chunks)
                        encoding = response.encoding or "utf-8"
                        body = raw.decode(encoding, errors="replace")
                        break
                else:
                    raise WebScrapeError("The website redirected too many times.")
        except WebScrapeError:
            raise
        except httpx.HTTPStatusError as exc:
            raise WebScrapeError(
                f"The website returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise WebScrapeError("The website could not be downloaded.") from exc

        if "text/plain" in content_type:
            title, text = "", " ".join(body.split())
            links = ()
            seo = None
        else:
            title, text, links, seo = inspect_page_data(body, url)
        text = text[:MAX_PAGE_CHARACTERS].strip()
        if not text:
            raise WebScrapeError("No readable text was found on that webpage.")

        page = WebPage(
            url=url,
            title=title or url,
            text=text,
            links=links,
            seo=seo,
            response_time_ms=round((time.perf_counter() - request_started) * 1000),
            response_bytes=len(raw),
        )
        self._cache[requested_url] = (time.monotonic(), page)
        return page

    async def sitemap_urls(self, root_url: str) -> list[str]:
        """Find same-domain page URLs exposed through common XML sitemaps."""
        parsed = urlsplit(root_url)
        base = urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))
        candidates = [
            urljoin(base, "robots.txt"),
            urljoin(base, "sitemap.xml"),
            urljoin(base, "wp-sitemap.xml"),
        ]
        sitemap_candidates: list[str] = []
        seen_candidates: set[str] = set()
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                for candidate in candidates:
                    response = await client.get(candidate)
                    if response.status_code >= 400:
                        continue
                    content_type = response.headers.get("content-type", "").lower()
                    body = response.text[:1_000_000]
                    if candidate.endswith("robots.txt"):
                        for line in body.splitlines():
                            if line.lower().startswith("sitemap:"):
                                sitemap = line.split(":", 1)[1].strip()
                                if sitemap and sitemap not in seen_candidates:
                                    sitemap_candidates.append(sitemap)
                                    seen_candidates.add(sitemap)
                    elif "xml" in content_type or body.lstrip().startswith("<"):
                        if candidate not in seen_candidates:
                            sitemap_candidates.append(candidate)
                            seen_candidates.add(candidate)

                urls: list[str] = []
                seen_urls: set[str] = set()
                pending = sitemap_candidates[:8]
                seen_sitemaps: set[str] = set()
                while pending and len(urls) < MAX_SITE_PAGES:
                    sitemap = pending.pop(0)
                    if sitemap in seen_sitemaps:
                        continue
                    seen_sitemaps.add(sitemap)
                    response = await client.get(sitemap)
                    if response.status_code >= 400:
                        continue
                    try:
                        document = ElementTree.fromstring(response.text[:2_000_000])
                    except ElementTree.ParseError:
                        continue
                    for node in document.iter():
                        if not node.tag.endswith("loc") or not node.text:
                            continue
                        location = urlunsplit((*urlsplit(node.text.strip())[:3], "", ""))
                        if location.endswith(".xml"):
                            if location not in seen_sitemaps and len(pending) < 20:
                                pending.append(location)
                        elif location not in seen_urls and _can_crawl(root_url, location):
                            urls.append(location)
                            seen_urls.add(location)
                            if len(urls) >= MAX_SITE_PAGES:
                                break
                return urls
        except (httpx.HTTPError, OSError, ValueError):
            return []

    async def wordpress_page_urls(self, root_url: str) -> list[str]:
        """Discover published WordPress pages through the REST API when available.

        The API is used only as an URL inventory. Each URL is still fetched from
        the public page so the audit uses the rendered HTML metadata and content.
        Sites without a public REST API simply return no results and use the
        normal sitemap/link crawl.
        """
        parsed = urlsplit(root_url)
        origin = urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))
        candidates = [
            urljoin(origin, "wp-json/wp/v2/pages"),
            urljoin(root_url, "wp-json/wp/v2/pages"),
        ]
        timeout = httpx.Timeout(connect=5.0, read=12.0, write=5.0, pool=5.0)
        headers = {"User-Agent": "OptiMind/0.1 (+local website analysis)"}

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                follow_redirects=True,
            ) as client:
                for endpoint in dict.fromkeys(candidates):
                    urls: list[str] = []
                    seen: set[str] = set()
                    for page_number in range(1, MAX_SITE_PAGES + 1):
                        response = await client.get(
                            endpoint,
                            params={
                                "per_page": min(100, MAX_SITE_PAGES),
                                "page": page_number,
                                "_fields": "link",
                                "status": "publish",
                            },
                        )
                        if response.status_code in {400, 401, 403, 404}:
                            break
                        response.raise_for_status()
                        payload = response.json()
                        if not isinstance(payload, list) or not payload:
                            break
                        for item in payload:
                            if not isinstance(item, dict) or not isinstance(item.get("link"), str):
                                continue
                            location = urlunsplit((*urlsplit(item["link"].strip())[:3], "", ""))
                            key = _page_key(location)
                            if key not in seen and _can_crawl(root_url, location):
                                urls.append(location)
                                seen.add(key)
                                if len(urls) >= MAX_SITE_PAGES:
                                    return urls
                        total_pages = int(response.headers.get("X-WP-TotalPages", page_number))
                        if page_number >= total_pages or len(payload) < min(100, MAX_SITE_PAGES):
                            break
                    if urls:
                        return urls
        except (httpx.HTTPError, OSError, ValueError, TypeError):
            return []
        return []

    async def scrape_site(self, requested_url: str) -> list[WebPage]:
        root = await self.scrape(requested_url)
        pages = [root]
        visited = {_page_key(root.url)}
        queue = []
        queued: set[str] = set()
        for link in await self.wordpress_page_urls(root.url):
            key = _page_key(link)
            if key not in visited and key not in queued:
                queue.append((link, 1))
                queued.add(key)
        for link in await self.sitemap_urls(root.url):
            key = _page_key(link)
            if key not in visited and key not in queued:
                queue.append((link, 1))
                queued.add(key)
        for link in root.links:
            key = _page_key(link)
            if key not in visited and key not in queued and _can_crawl(root.url, link):
                queue.append((link, 1))
                queued.add(key)

        while queue and len(pages) < MAX_SITE_PAGES:
            url, depth = queue.pop(0)
            key = _page_key(url)
            if key in visited or depth > MAX_CRAWL_DEPTH:
                continue
            visited.add(key)
            try:
                page = await self.scrape(url)
            except WebScrapeError:
                continue
            page_key = _page_key(page.url)
            duplicate_page = any(_page_key(existing.url) == page_key for existing in pages)
            if duplicate_page:
                continue
            visited.add(page_key)
            pages.append(page)
            if depth < MAX_CRAWL_DEPTH:
                for link in page.links:
                    link_key = _page_key(link)
                    if (
                        link_key not in visited
                        and link_key not in queued
                        and _can_crawl(root.url, link)
                    ):
                        queue.append((link, depth + 1))
                        queued.add(link_key)
        return pages

    async def pages_from_messages(self, messages: list[object]) -> list[WebPage]:
        urls: list[str] = []
        for message in reversed(messages):
            if getattr(message, "role", "") != "user":
                continue
            content = getattr(message, "content", "")
            for url in extract_urls(content):
                if url not in urls:
                    urls.append(url)
                if len(urls) == MAX_INPUT_URLS:
                    break
            if len(urls) == MAX_INPUT_URLS:
                break

        pages: list[WebPage] = []
        seen: set[str] = set()
        for url in urls:
            for page in await self.scrape_site(url):
                key = _page_key(page.url)
                if key not in seen:
                    pages.append(page)
                    seen.add(key)
                if len(pages) == MAX_SITE_PAGES:
                    return pages
        return pages


web_scraper = WebScraper()
