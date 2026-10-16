import base64
import io
import json
import re
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.core.config import settings
from app.schemas.chat import ChatImage


class ImageGenerationError(Exception):
    pass


QUOTED_TEXT_PATTERN = re.compile(r'["“”]([^"“”]{1,100})["“”]')
TEXT_REQUEST_PATTERN = re.compile(
    r'(?:that\s+)?(?:clearly\s+)?(?:spells?\s+out|reads?|says?)\s*'
    r'["“”][^"“”]{1,100}["“”](?:\s+in\s+[^,]+)?',
    re.IGNORECASE,
)


def _extract_exact_text(prompt: str) -> str | None:
    matches = [match.strip() for match in QUOTED_TEXT_PATTERN.findall(prompt)]
    return " · ".join(match for match in matches if match) or None


def _prepare_visual_prompt(prompt: str, exact_text: str | None) -> str:
    if not exact_text:
        return prompt
    prepared = TEXT_REQUEST_PATTERN.sub(
        "with a clean empty central display panel containing no letters or words",
        prompt,
    )
    return QUOTED_TEXT_PATTERN.sub("an empty sign panel", prepared)


def _load_overlay_font(
    size: int, script: bool = False
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    script_candidates = (
        Path("/System/Library/Fonts/Supplemental/Snell Roundhand.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        Path("C:/Windows/Fonts/segoesc.ttf"),
    )
    standard_candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    )
    candidates = script_candidates + standard_candidates if script else standard_candidates
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _overlay_exact_text(encoded_image: str, text: str, prompt: str) -> str:
    try:
        image = Image.open(io.BytesIO(base64.b64decode(encoded_image))).convert("RGBA")
    except (OSError, ValueError) as exc:
        raise ImageGenerationError("The generated image could not be processed.") from exc

    width, height = image.size
    max_width = int(width * 0.82)
    font_size = max(18, int(width * 0.12))
    script = "script" in prompt.lower() or "handwritten" in prompt.lower()
    while font_size > 18:
        font = _load_overlay_font(font_size, script=script)
        box = ImageDraw.Draw(image).textbbox((0, 0), text, font=font, stroke_width=1)
        if box[2] - box[0] <= max_width:
            break
        font_size -= 2
    else:
        font = _load_overlay_font(18, script=script)

    draw = ImageDraw.Draw(image)
    box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    panel_left = int(width * 0.07)
    panel_right = int(width * 0.93)
    panel_top = int(height * 0.35)
    panel_bottom = int(height * 0.65)

    panel = Image.new("RGBA", image.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle(
        (
            panel_left,
            panel_top,
            panel_right,
            panel_bottom,
        ),
        radius=max(10, width // 40),
        fill=(8, 8, 14, 185),
        outline=(255, 255, 255, 55),
        width=1,
    )
    image = Image.alpha_composite(image, panel)

    neon = "neon" in prompt.lower()
    pink = "pink" in prompt.lower()
    color = (255, 48, 205, 255) if pink else (110, 220, 255, 255)
    if not neon:
        color = (255, 255, 255, 255)

    if neon:
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.text((x, y), text, font=font, fill=color, stroke_width=3, stroke_fill=color)
        glow = glow.filter(ImageFilter.GaussianBlur(radius=max(4, width // 64)))
        image = Image.alpha_composite(image, glow)

    final_draw = ImageDraw.Draw(image)
    final_draw.text(
        (x, y),
        text,
        font=font,
        fill=color,
        stroke_width=1 if neon else 2,
        stroke_fill=(255, 190, 240, 255) if pink else (0, 0, 0, 230),
    )

    output = io.BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return base64.b64encode(output.getvalue()).decode()


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

        exact_text = _extract_exact_text(prompt)
        visual_prompt = _prepare_visual_prompt(prompt, exact_text)
        weighted_prompt = (
            f"({visual_prompt}:1.35), exact requested colors, accurate object attributes, "
            "clean composition, high detail"
        )
        negative_prompt = (
            "wrong colors, inaccurate colors, color mismatch, extra objects, "
            "deformed, distorted, blurry, low quality"
        )
        if exact_text:
            negative_prompt += ", letters, words, text, typography, watermark"
        extra_args = {
            "negative_prompt": negative_prompt,
            "sample_params": {
                "sample_steps": settings.image_generation_steps,
                "sample_method": settings.image_generation_sampler,
                "guidance": {"txt_cfg": settings.image_generation_cfg_scale},
            },
        }
        enhanced_prompt = (
            f"{weighted_prompt} <sd_cpp_extra_args>"
            f"{json.dumps(extra_args, separators=(',', ':'))}"
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
        if exact_text:
            encoded_image = _overlay_exact_text(encoded_image, exact_text, prompt)
        return ChatImage(
            name="optimind-generated.png",
            media_type="image/png",
            data=encoded_image,
        )


image_generation_service = ImageGenerationService()
