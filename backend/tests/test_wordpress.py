import pytest

from app.services.wordpress import (
    WordPressConnectionError,
    default_wordpress_api_url,
    normalize_website_url,
)


def test_website_url_adds_https_and_removes_query() -> None:
    assert normalize_website_url("example.com/blog/?preview=1") == (
        "https://example.com/blog"
    )


def test_wordpress_api_url_respects_subdirectory() -> None:
    assert default_wordpress_api_url("https://example.com/blog") == (
        "https://example.com/blog/wp-json/"
    )


def test_website_url_rejects_credentials() -> None:
    with pytest.raises(WordPressConnectionError, match="credentials"):
        normalize_website_url("https://user:secret@example.com")
