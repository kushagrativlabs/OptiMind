import pytest

from app.services.web_scraper import (
    WebScrapeError,
    extract_page_data,
    extract_readable_text,
    extract_urls,
    validate_public_url,
)


def test_extract_urls_removes_sentence_punctuation() -> None:
    assert extract_urls("Read https://example.com/docs, then https://example.com/about.") == [
        "https://example.com/docs",
        "https://example.com/about",
    ]


def test_extract_urls_accepts_a_domain_without_a_scheme() -> None:
    assert extract_urls("Please inspect sample.com and summarize it.") == [
        "https://sample.com"
    ]


def test_extract_readable_text_skips_scripts_and_styles() -> None:
    title, text = extract_readable_text(
        "<html><head><title>Example</title><style>hidden</style></head>"
        "<body><h1>Hello</h1><script>ignore me</script><p>Useful text</p></body></html>"
    )

    assert title == "Example"
    assert "Hello" in text
    assert "Useful text" in text
    assert "hidden" not in text
    assert "ignore me" not in text


def test_extract_page_data_resolves_internal_links() -> None:
    _, _, links = extract_page_data(
        '<a href="/about">About</a><a href="https://other.example/contact">Other</a>',
        "https://sample.com/",
    )

    assert links == (
        "https://sample.com/about",
        "https://other.example/contact",
    )


@pytest.mark.asyncio
async def test_private_urls_are_rejected() -> None:
    with pytest.raises(WebScrapeError, match="Private and local"):
        await validate_public_url("http://127.0.0.1/private")
