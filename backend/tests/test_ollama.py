from unittest.mock import AsyncMock

import pytest

from app.schemas.chat import OllamaModel
from app.services.ollama import OllamaModelError, OllamaService


@pytest.mark.asyncio
async def test_image_processing_requires_a_vision_model() -> None:
    service = OllamaService()
    service.models = AsyncMock(
        return_value=[
            OllamaModel(
                name="text-only:latest",
                size=100,
                capabilities=["completion"],
            )
        ]
    )

    with pytest.raises(OllamaModelError, match="vision-capable"):
        await service.validate_model("text-only:latest", require_vision=True)


@pytest.mark.asyncio
async def test_image_processing_accepts_a_vision_model() -> None:
    service = OllamaService()
    service.models = AsyncMock(
        return_value=[
            OllamaModel(
                name="vision:latest",
                size=100,
                capabilities=["completion", "vision"],
            )
        ]
    )

    assert await service.validate_model("vision:latest", require_vision=True) == (
        "vision:latest"
    )
