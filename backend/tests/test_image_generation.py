import base64

import httpx
import pytest

from app.services.image_generation import ImageGenerationError, ImageGenerationService


@pytest.mark.asyncio
async def test_image_generation_returns_png() -> None:
    encoded = base64.b64encode(b"generated png").decode()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/images/generations"
        return httpx.Response(200, json={"data": [{"b64_json": encoded}]})

    service = ImageGenerationService(
        base_url="http://image.test",
        enabled=True,
        transport=httpx.MockTransport(handler),
    )
    image = await service.generate("a green website dashboard")

    assert image.media_type == "image/png"
    assert image.data == encoded


@pytest.mark.asyncio
async def test_image_generation_requires_enabled_service() -> None:
    service = ImageGenerationService(enabled=False)

    with pytest.raises(ImageGenerationError, match="disabled"):
        await service.generate("a green website dashboard")
