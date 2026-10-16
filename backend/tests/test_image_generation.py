import base64
import json

import httpx
import pytest

from app.services.image_generation import (
    ImageGenerationError,
    ImageGenerationService,
    _extract_exact_text,
    _prepare_visual_prompt,
)


def test_quoted_text_is_reserved_for_exact_overlay() -> None:
    prompt = 'A neon sign that clearly spells out "MIDNIGHT CAFE" in pink script, on brick.'

    exact_text = _extract_exact_text(prompt)
    visual_prompt = _prepare_visual_prompt(prompt, exact_text)

    assert exact_text == "MIDNIGHT CAFE"
    assert "MIDNIGHT CAFE" not in visual_prompt
    assert "no letters or words" in visual_prompt


@pytest.mark.asyncio
async def test_image_generation_returns_png() -> None:
    encoded = base64.b64encode(b"generated png").decode()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/images/generations"
        prompt = json.loads(request.read())["prompt"]
        assert "(a green website dashboard:1.35)" in prompt
        assert "wrong colors" in prompt
        assert '"sample_method":"lcm"' in prompt
        assert '"txt_cfg":1.0' in prompt
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
