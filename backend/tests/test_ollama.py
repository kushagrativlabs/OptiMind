from unittest.mock import AsyncMock

import pytest

from app.schemas.chat import OllamaModel
from app.services.ollama import OllamaModelError, OllamaService, generation_metrics


def test_generation_metrics_use_ollama_evaluation_duration() -> None:
    metrics = generation_metrics(
        {
            "total_duration": 2_500_000_000,
            "eval_duration": 2_000_000_000,
            "eval_count": 20,
        }
    )

    assert metrics is not None
    assert metrics.duration_seconds == 2.5
    assert metrics.tokens_per_second == 10.0
    assert metrics.output_tokens == 20


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
