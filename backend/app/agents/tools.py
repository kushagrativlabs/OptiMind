import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.schemas.chat import AgentActivity, ChatMessage
from app.services.web_scraper import (
    MAX_SITE_PAGES,
    WebScrapeError,
    extract_urls,
    web_scraper,
)
from app.services.web_search import WebSearchError, web_search_service
from app.services.wordpress_pages import WordPressPagesError, fetch_wordpress_pages
from app.services.lighthouse import LIGHTHOUSE_MAX_PAGES, LighthouseError, run_lighthouse

WEBSITE_TASK_PATTERN = re.compile(
    r"\b(?:analy[sz]e|audit|check|crawl|inspect|review|scan|seo|aeo|geo|summari[sz]e)\b",
    re.IGNORECASE,
)
AUTO_WEB_SEARCH_PATTERN = re.compile(
    r"\b(?:latest|current|today|recent|news|search|google|competitor|trend|research|"
    r"source|sources|citation|citations|price|pricing|release|version|law|regulation)\b",
    re.IGNORECASE,
)
# Queries for live prices, rates, quotes, and market data must never be
# answered from the local model's memory. They require a successful search.
LIVE_DATA_PATTERN = re.compile(
    r"\b(?:price|prices|rate|rates|quote|quotes|market|exchange rate|forex|fuel|"
    r"petrol|diesel|inflation)\b|\b(?:gold|silver|bitcoin|btc|stock|stocks)\b"
    r"(?=.*\b(?:current|today|latest|price|rate|quote|market)\b)",
    re.IGNORECASE,
)
NO_WEB_SEARCH_PATTERN = re.compile(
    r"\b(?:do not|don't|dont|without|no)\s+(?:use\s+)?(?:the\s+)?(?:web\s+)?search\b|\boffline\b",
    re.IGNORECASE,
)
LOCAL_CREATIVE_PATTERN = re.compile(
    r"\b(?:draft|write|rewrite|brainstorm|translate|format|code|debug|summari[sz]e)\b",
    re.IGNORECASE,
)


class AgentToolError(Exception):
    pass


class SearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class WebpageInput(BaseModel):
    url: str = Field(min_length=1, max_length=2_000)


class WordPressPagesInput(BaseModel):
    url: str = Field(min_length=1, max_length=2_000)
    website_url: str = Field(min_length=1, max_length=2_000)


class ToolMetadata(BaseModel):
    name: str
    description: str
    permission: Literal["read_only", "changes_data"]


class ToolCall(BaseModel):
    id: str
    name: str
    label: str
    arguments: dict[str, str]

    def activity(self, status: str, detail: str = "") -> AgentActivity:
        return AgentActivity(
            id=self.id,
            tool=self.name,
            label=self.label,
            status=status,
            detail=detail,
        )


class ToolSource(BaseModel):
    url: str
    title: str
    content: str


class ToolResult(BaseModel):
    call: ToolCall
    sources: list[ToolSource]
    detail: str


async def _with_lighthouse(pages: list[object]) -> tuple[list[object], int]:
    """Attach local Lighthouse metrics without failing the website audit."""
    audited: list[object] = []
    measured = 0
    for page in pages:
        if measured >= LIGHTHOUSE_MAX_PAGES:
            audited.append(page)
            continue
        try:
            metrics = await run_lighthouse(page.url)
        except LighthouseError:
            audited.append(page)
            continue
        audited.append(replace(page, lighthouse=metrics))
        measured += 1
    return audited, measured


def page_source_content(page: object, compact: bool = False) -> str:
    seo = getattr(page, "seo", None)
    if seo is None:
        return getattr(page, "text", "")
    headings = ", ".join(f"{level}: {text}" for level, text in seo.headings) or "None found"
    schemas = ", ".join(seo.schema_types) or "None found"
    quality_flags = ", ".join(seo.quality_flags) or "None detected"
    lighthouse = getattr(page, "lighthouse", None) or {}
    performance = lighthouse.get("performance", "NOT MEASURED")
    accessibility = lighthouse.get("accessibility", "NOT MEASURED")
    best_practices = lighthouse.get("best_practices", "NOT MEASURED")
    lighthouse_seo = lighthouse.get("seo", "NOT MEASURED")
    lcp = lighthouse.get("lcp_ms", "NOT MEASURED")
    cls = lighthouse.get("cls", "NOT MEASURED")
    inp = lighthouse.get("inp_ms", "NOT MEASURED")
    if compact:
        summary = " ".join(getattr(page, "text", "").split())[:240]
        return (
            "VERIFIED PAGE AUDIT RECORD:\n"
            f"URL: {getattr(page, 'url', 'NOT FOUND')}\n"
            f"Title: {page.title or 'NOT FOUND'}\n"
            f"Meta description: {seo.meta_description or 'NOT FOUND'}\n"
            f"Canonical: {seo.canonical_url or 'NOT FOUND'}\n"
            f"Robots: {seo.robots or 'NOT FOUND'}\n"
            f"Headings: {headings}\n"
            f"Schema: {schemas}\n"
            f"Images: {seo.image_count}; missing alt: {seo.images_missing_alt}\n"
            f"Quality flags: {quality_flags}\n"
            f"Observed response time: {getattr(page, 'response_time_ms', None) or 'NOT MEASURED'} ms\n"
            f"Response size: {getattr(page, 'response_bytes', None) or 'NOT MEASURED'} bytes\n"
            f"Lighthouse performance: {performance}; accessibility: {accessibility}; best practices: {best_practices}; SEO: {lighthouse_seo}\n"
            f"Core Web Vitals: LCP {lcp} ms; CLS {cls}; INP {inp} ms\n"
            f"Content summary: {summary or 'NOT FOUND'}"
        )
    return (
        "VERIFIED PAGE SEO EVIDENCE:\n"
        f"Title tag: {page.title or 'NOT FOUND'}\n"
        f"Meta description: {seo.meta_description or 'NOT FOUND'}\n"
        f"Canonical URL: {seo.canonical_url or 'NOT FOUND'}\n"
        f"Robots: {seo.robots or 'NOT FOUND'}\n"
        f"Headings: {headings}\n"
        f"JSON-LD schema types: {schemas}\n"
        f"Images: {seo.image_count}; images missing alt: {seo.images_missing_alt}\n\n"
        f"Quality flags: {quality_flags}\n\n"
        f"Observed response time: {getattr(page, 'response_time_ms', None) or 'NOT MEASURED'} ms\n"
        f"Response size: {getattr(page, 'response_bytes', None) or 'NOT MEASURED'} bytes\n\n"
        f"Lighthouse performance: {performance}; accessibility: {accessibility}; best practices: {best_practices}; SEO: {lighthouse_seo}\n"
        f"Core Web Vitals: LCP {lcp} ms; CLS {cls}; INP {inp} ms\n\n"
        "READABLE PAGE CONTENT:\n"
        f"{page.text}"
    )


ToolHandler = Callable[[BaseModel], Awaitable[ToolResult]]


@dataclass(frozen=True)
class RegisteredTool:
    metadata: ToolMetadata
    input_model: type[BaseModel]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        if tool.metadata.name in self._tools:
            raise ValueError(f"Tool {tool.metadata.name} is already registered.")
        self._tools[tool.metadata.name] = tool

    def metadata(self) -> list[ToolMetadata]:
        return [tool.metadata for tool in self._tools.values()]

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None:
            raise AgentToolError(f"Unknown tool: {call.name}")
        if tool.metadata.permission != "read_only":
            raise AgentToolError(f"Tool {call.name} requires change permission.")
        try:
            tool_input = tool.input_model.model_validate(call.arguments)
            result = await tool.handler(tool_input)
        except ValidationError as exc:
            raise AgentToolError(f"Invalid input for {call.name}.") from exc
        except (WebScrapeError, WebSearchError, WordPressPagesError) as exc:
            raise AgentToolError(str(exc)) from exc
        return result.model_copy(update={"call": call})


async def _search(input_data: BaseModel) -> ToolResult:
    request = SearchInput.model_validate(input_data)
    results = await web_search_service.search(request.query)
    sources = [
        ToolSource(url=result.url, title=result.title, content=result.content)
        for result in results
    ]
    return ToolResult(
        call=ToolCall(id="pending", name="web_search", label="Search the web", arguments={}),
        sources=sources,
        detail=f"Found {len(sources)} current search results.",
    )


async def _read_webpage(input_data: BaseModel) -> ToolResult:
    request = WebpageInput.model_validate(input_data)
    page = await web_scraper.scrape(request.url)
    return ToolResult(
        call=ToolCall(id="pending", name="read_webpage", label="Read webpage", arguments={}),
        sources=[ToolSource(url=page.url, title=page.title, content=page_source_content(page))],
        detail="Read one public webpage.",
    )


async def _crawl_website(input_data: BaseModel) -> ToolResult:
    request = WebpageInput.model_validate(input_data)
    pages = await web_scraper.scrape_site(request.url)
    pages, measured = await _with_lighthouse(pages)
    return ToolResult(
        call=ToolCall(id="pending", name="crawl_website", label="Crawl website", arguments={}),
        sources=[
            ToolSource(
                url=page.url,
                title=page.title,
                content=page_source_content(page, compact=True),
            )
            for page in pages
        ],
        detail=(
            f"Read {len(pages)} page{'s' if len(pages) != 1 else ''} from the website."
            f" Local Lighthouse metrics measured for {measured} page{'s' if measured != 1 else ''}."
            + (
                f" The safety ceiling is {MAX_SITE_PAGES} pages."
                if len(pages) >= MAX_SITE_PAGES
                else ""
            )
        ),
    )


async def _read_wordpress_pages(input_data: BaseModel) -> ToolResult:
    request = WordPressPagesInput.model_validate(input_data)
    try:
        pages = await fetch_wordpress_pages(request.url, request.website_url)
        pages, measured = await _with_lighthouse(pages)
        detail = (
            f"Read {len(pages)} published page{'s' if len(pages) != 1 else ''} "
            f"from the WordPress REST API. Local Lighthouse metrics measured for {measured} "
            f"page{'s' if measured != 1 else ''}."
        )
    except WordPressPagesError:
        # A website can be WordPress without exposing the public REST pages
        # endpoint. Fall back to the normal public crawl so the audit still
        # discovers pages through sitemaps and internal links.
        pages = await web_scraper.scrape_site(request.website_url)
        if not pages:
            raise
        pages, measured = await _with_lighthouse(pages)
        detail = (
            f"WordPress pages API unavailable; read {len(pages)} public page"
            f"{'s' if len(pages) != 1 else ''} through sitemap and internal links. "
            f"Local Lighthouse metrics measured for {measured} page{'s' if measured != 1 else ''}."
        )
    return ToolResult(
        call=ToolCall(id="pending", name="read_wordpress_pages", label="Read WordPress pages", arguments={}),
        sources=[
            ToolSource(
                url=page.url,
                title=page.title,
                content=page_source_content(page, compact=True),
            )
            for page in pages
        ],
        detail=detail,
    )


class AgentTools:
    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self.registry.register(
            RegisteredTool(
                metadata=ToolMetadata(
                    name="web_search",
                    description="Search current public web results through local SearXNG.",
                    permission="read_only",
                ),
                input_model=SearchInput,
                handler=_search,
            )
        )
        self.registry.register(
            RegisteredTool(
                metadata=ToolMetadata(
                    name="read_webpage",
                    description="Read one public HTML or text webpage.",
                    permission="read_only",
                ),
                input_model=WebpageInput,
                handler=_read_webpage,
            )
        )
        self.registry.register(
            RegisteredTool(
                metadata=ToolMetadata(
                    name="crawl_website",
                    description="Read a public page and bounded same-domain inner pages.",
                    permission="read_only",
                ),
                input_model=WebpageInput,
                handler=_crawl_website,
            )
        )
        self.registry.register(
            RegisteredTool(
                metadata=ToolMetadata(
                    name="read_wordpress_pages",
                    description="Read published pages through the connected WordPress REST API.",
                    permission="read_only",
                ),
                input_model=WordPressPagesInput,
                handler=_read_wordpress_pages,
            )
        )

    def plan(
        self,
        messages: list[ChatMessage],
        use_web_search: bool,
        active_website_url: str | None = None,
        active_wordpress_api_url: str | None = None,
    ) -> list[ToolCall]:
        latest_user_message = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "",
        )
        calls: list[ToolCall] = []
        urls: list[str] = []
        for message in reversed(messages):
            if message.role != "user":
                continue
            for url in extract_urls(message.content):
                if url not in urls:
                    urls.append(url)
                if len(urls) == 2:
                    break
            if len(urls) == 2:
                break

        if (
            not urls
            and active_website_url
            and WEBSITE_TASK_PATTERN.search(latest_user_message)
        ):
            urls.append(active_website_url)

        for index, url in enumerate(urls, start=1):
            use_wordpress_api = bool(
                active_wordpress_api_url
                and active_website_url
                and url.rstrip("/") == active_website_url.rstrip("/")
            )
            calls.append(
                ToolCall(
                    id=f"crawl-{index}",
                    name="read_wordpress_pages" if use_wordpress_api else "crawl_website",
                    label="Read WordPress pages" if use_wordpress_api else f"Read {url}",
                    arguments=(
                        {"url": active_wordpress_api_url, "website_url": url}
                        if use_wordpress_api
                        else {"url": url}
                    ),
                )
            )
        message_word_count = len(re.findall(r"\b\w+\b", latest_user_message))
        is_website_audit = bool(
            active_website_url and WEBSITE_TASK_PATTERN.search(latest_user_message)
        )
        # Search ordinary factual phrases automatically, even when they do not
        # contain an obvious trigger word (for example, "Tiger Shroff bullet
        # attack"). Website audits already have their own page evidence, so do
        # not add a second search unless the user asks for current sources.
        automatic_factual_query = message_word_count >= 3 and not LOCAL_CREATIVE_PATTERN.search(
            latest_user_message
        )
        should_search = bool(
            latest_user_message.strip()
            and not NO_WEB_SEARCH_PATTERN.search(latest_user_message)
            and (
                use_web_search
                # Live data is never allowed to fall back to Ollama's memory.
                # If search is disabled/unavailable, execute() raises a clear
                # error instead of returning an invented number.
                or LIVE_DATA_PATTERN.search(latest_user_message)
                or (
                    settings.web_search_enabled
                    and (
                        AUTO_WEB_SEARCH_PATTERN.search(latest_user_message)
                        or (automatic_factual_query and not is_website_audit)
                    )
                )
            )
        )
        if should_search:
            calls.append(
                ToolCall(
                    id="search-1",
                    name="web_search",
                    label="Search the web for current sources",
                    arguments={"query": latest_user_message},
                )
            )
        return calls

    async def execute(self, call: ToolCall) -> ToolResult:
        return await self.registry.execute(call)


agent_tools = AgentTools()
