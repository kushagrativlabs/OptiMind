import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.schemas.chat import ChatMessage, OllamaChatResponse, OllamaModel


class OllamaConnectionError(Exception):
    pass


class OllamaModelError(Exception):
    pass


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    async def status(self) -> dict[str, str]:
        try:
            models = await self.models()
        except OllamaConnectionError as exc:
            return {"status": "offline", "detail": f"Ollama unavailable: {type(exc).__name__}"}

        model_names = {model.name for model in models}
        model_available = self.model in model_names or any(
            name.startswith(f"{self.model}:") for name in model_names
        )
        if not model_available:
            return {
                "status": "offline",
                "detail": f"Ollama is online, but {self.model} is not installed",
            }
        return {"status": "online", "detail": "Ollama and the configured model are ready"}

    async def models(self) -> list[OllamaModel]:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            raise OllamaConnectionError("Ollama is offline. Start Ollama and try again.") from exc

        return sorted(
            [
                OllamaModel(name=item["name"], size=item.get("size", 0))
                for item in response.json().get("models", [])
                if item.get("name")
            ],
            key=lambda model: model.name.lower(),
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        requested_model: str | None = None,
    ) -> OllamaChatResponse:
        model = requested_model or self.model
        installed_models = {item.name for item in await self.models()}
        if model not in installed_models:
            raise OllamaModelError(f"Model {model} is not installed in Ollama.")

        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaConnectionError("Ollama is offline. Start Ollama and try again.") from exc
        except httpx.HTTPStatusError as exc:
            detail = "Ollama rejected the request"
            if exc.response.status_code == 404:
                detail = f"Model {model} is not installed. Run: ollama pull {model}"
            raise OllamaConnectionError(detail) from exc
        except httpx.HTTPError as exc:
            raise OllamaConnectionError("Ollama did not complete the request.") from exc

        content = response.json().get("message", {}).get("content")
        if not content:
            raise OllamaConnectionError("Ollama returned an empty response.")
        return OllamaChatResponse(
            message=ChatMessage(role="assistant", content=content),
            model=model,
        )

    async def validate_model(self, requested_model: str | None = None) -> str:
        model = requested_model or self.model
        installed_models = {item.name for item in await self.models()}
        if model not in installed_models:
            raise OllamaModelError(f"Model {model} is not installed in Ollama.")
        return model

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        requested_model: str | None = None,
    ) -> AsyncIterator[str]:
        model = requested_model or self.model
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in messages],
            "stream": True,
        }
        timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        item = json.loads(line)
                        content = item.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if item.get("done"):
                            break
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                "Ollama is offline. Start Ollama and try again."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = "Ollama rejected the request"
            if exc.response.status_code == 404:
                detail = f"Model {model} is not installed. Run: ollama pull {model}"
            raise OllamaConnectionError(detail) from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise OllamaConnectionError("Ollama did not complete the request.") from exc
