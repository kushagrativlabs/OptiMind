import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.schemas.chat import AgentActivity, ChatMessage
from app.services.web_scraper import (
    MAX_SITE_PAGES,
    WebScrapeError,
    extract_urls,
    web_scraper,
)
from app.services.web_search import WebSearchError, web_search_service

WEBSITE_TASK_PATTERN = re.compile(
    r"\b(?:analy[sz]e|audit|check|crawl|inspect|review|scan|seo|aeo|geo|summari[sz]e)\b",
    re.IGNORECASE,
)


class AgentToolError(Exception):
    pass


class SearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class WebpageInput(BaseModel):
    url: str = Field(min_length=1, max_length=2_000)


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


def page_source_content(page: object, compact: bool = False) -> str:
    seo = getattr(page, "seo", None)
    if seo is None:
        return getattr(page, "text", "")
    headings = ", ".join(f"{level}: {text}" for level, text in seo.headings) or "None found"
    schemas = ", ".join(seo.schema_types) or "None found"
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
        except (WebScrapeError, WebSearchError) as exc:
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
            + (
                f" The safety ceiling is {MAX_SITE_PAGES} pages."
                if len(pages) >= MAX_SITE_PAGES
                else ""
            )
        ),
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

    def plan(
        self,
        messages: list[ChatMessage],
        use_web_search: bool,
        active_website_url: str | None = None,
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
            calls.append(
                ToolCall(
                    id=f"crawl-{index}",
                    name="crawl_website",
                    label=f"Read {url}",
                    arguments={"url": url},
                )
            )
        if use_web_search and latest_user_message.strip():
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
