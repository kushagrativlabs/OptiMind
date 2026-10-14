import asyncio
import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

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
MAX_SITE_PAGES = 8
MAX_CRAWL_DEPTH = 2
CACHE_SECONDS = 600


class WebScrapeError(Exception):
    pass


@dataclass(frozen=True)
class WebPage:
    url: str
    title: str
    text: str
    links: tuple[str, ...] = ()


class ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.links: list[str] = []
        self.skipped_depth = 0
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in SKIPPED_TAGS:
            self.skipped_depth += 1
        elif tag == "a" and self.skipped_depth == 0:
            href = next((value for name, value in attrs if name.lower() == "href"), None)
            if href:
                self.links.append(href)
        elif tag == "title" and self.skipped_depth == 0:
            self.in_title = True
        elif tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "article", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIPPED_TAGS and self.skipped_depth:
            self.skipped_depth -= 1
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.skipped_depth or not data.strip():
            return
        if self.in_title:
            self.title_parts.append(data)
        else:
            self.parts.append(data)

    def result(self) -> tuple[str, str]:
        title = " ".join(" ".join(self.title_parts).split())
        text = re.sub(r"\n\s*\n+", "\n", "".join(self.parts))
        text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
        return title, text


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
    return title, text, tuple(links)


def _site_hostname(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").lower()
    return hostname.removeprefix("www.")


def _can_crawl(root_url: str, candidate_url: str) -> bool:
    parsed = urlsplit(candidate_url)
    if _site_hostname(candidate_url) != _site_hostname(root_url):
        return False
    path = parsed.path.lower().rstrip("/")
    return not any(path.endswith(extension) for extension in SKIPPED_EXTENSIONS)


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
        else:
            title, text, links = extract_page_data(body, url)
        text = text[:MAX_PAGE_CHARACTERS].strip()
        if not text:
            raise WebScrapeError("No readable text was found on that webpage.")

        page = WebPage(url=url, title=title or url, text=text, links=links)
        self._cache[requested_url] = (time.monotonic(), page)
        return page

    async def scrape_site(self, requested_url: str) -> list[WebPage]:
        root = await self.scrape(requested_url)
        parsed_root = urlsplit(root.url)
        if parsed_root.path not in {"", "/"} or parsed_root.query:
            return [root]

        pages = [root]
        visited = {root.url}
        queue = [(link, 1) for link in root.links if _can_crawl(root.url, link)]

        while queue and len(pages) < MAX_SITE_PAGES:
            url, depth = queue.pop(0)
            if url in visited or depth > MAX_CRAWL_DEPTH:
                continue
            visited.add(url)
            try:
                page = await self.scrape(url)
            except WebScrapeError:
                continue
            pages.append(page)
            if depth < MAX_CRAWL_DEPTH:
                queue.extend(
                    (link, depth + 1)
                    for link in page.links
                    if link not in visited and _can_crawl(root.url, link)
                )
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
                if page.url not in seen:
                    pages.append(page)
                    seen.add(page.url)
                if len(pages) == MAX_SITE_PAGES:
                    return pages
        return pages


web_scraper = WebScraper()
