import httpx

from app.core.config import settings
from app.schemas.chat import ChatImage


class ImageGenerationError(Exception):
    pass


class ImageGenerationService:
    def __init__(
        self,
        base_url: str | None = None,
        enabled: bool | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.image_generation_base_url).rstrip("/")
        self.enabled = settings.image_generation_enabled if enabled is None else enabled
        self.transport = transport

    async def status(self) -> dict[str, str]:
        if not self.enabled:
            return {
                "status": "offline",
                "detail": "Local image generation is disabled in configuration.",
            }
        try:
            async with httpx.AsyncClient(
                timeout=3.0,
                transport=self.transport,
            ) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                response.raise_for_status()
        except (httpx.HTTPError, OSError):
            return {
                "status": "offline",
                "detail": "Image generator is not running. Run npm run image:start.",
            }
        return {
            "status": "online",
            "detail": f"{settings.image_generation_model} is ready",
        }

    async def generate(self, prompt: str) -> ChatImage:
        if not self.enabled:
            raise ImageGenerationError(
                "Image generation is disabled. Enable IMAGE_GENERATION_ENABLED first."
            )

        enhanced_prompt = (
            f"{prompt} <sd_cpp_extra_args>"
            f'{{"sample_params":{{"sample_steps":{settings.image_generation_steps}}}}}'
            "</sd_cpp_extra_args>"
        )
        timeout = httpx.Timeout(connect=5.0, read=900.0, write=30.0, pool=5.0)
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/v1/images/generations",
                    json={
                        "prompt": enhanced_prompt,
                        "n": 1,
                        "size": settings.image_generation_size,
                        "output_format": "png",
                    },
                )
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ImageGenerationError(
                "Image generator is offline. Run npm run image:start and try again."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = "The image generator rejected the request."
            try:
                body = exc.response.json()
                detail = str(body.get("error") or body.get("detail") or detail)
            except ValueError:
                pass
            raise ImageGenerationError(detail) from exc
        except httpx.HTTPError as exc:
            raise ImageGenerationError("Image generation did not complete.") from exc

        data = response.json().get("data", [])
        encoded_image = data[0].get("b64_json") if data else None
        if not encoded_image:
            raise ImageGenerationError("The image generator returned no image.")
        return ChatImage(
            name="optimind-generated.png",
            media_type="image/png",
            data=encoded_image,
        )


image_generation_service = ImageGenerationService()
