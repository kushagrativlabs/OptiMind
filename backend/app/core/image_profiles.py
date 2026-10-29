from typing import TypedDict


class ImageProfile(TypedDict):
    label: str
    backend: str
    base_url_env: str
    model: str
    steps: int
    cfg_scale: float
    sampler: str
    recommended: bool
    note: str


IMAGE_PROFILES: dict[str, ImageProfile] = {
    "fast": {
        "label": "Fast LCM (recommended)",
        "backend": "stable-diffusion.cpp",
        "base_url_env": "IMAGE_GENERATION_BASE_URL",
        "model": "lcm-ssd-1b-q4",
        "steps": 4,
        "cfg_scale": 1.0,
        "sampler": "lcm",
        "recommended": True,
        "note": "Fast 512px generation for an 8 GB M2.",
    },
    "sd15": {
        "label": "Stable Diffusion 1.5 (experimental)",
        "backend": "stable-diffusion.cpp",
        "base_url_env": "IMAGE_GENERATION_BASE_URL",
        "model": "stable-diffusion-v1-5-q4",
        "steps": 12,
        "cfg_scale": 7.5,
        "sampler": "euler_a",
        "recommended": False,
        "note": "Higher-step profile; slower and currently experimental in this build.",
    },
    "custom": {
        "label": "Custom model",
        "backend": "custom",
        "base_url_env": "IMAGE_GENERATION_BASE_URL",
        "model": "custom",
        "steps": 4,
        "cfg_scale": 1.0,
        "sampler": "lcm",
        "recommended": False,
        "note": "Uses IMAGE_GENERATION_MODEL_PATH and the custom sampling settings.",
    },
    "diffusers": {
        "label": "Diffusers worker",
        "backend": "diffusers",
        "base_url_env": "IMAGE_GENERATION_DIFFUSERS_BASE_URL",
        "model": "diffusers-model",
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler": "euler",
        "recommended": False,
        "note": "Requires an OpenAI-compatible Diffusers image worker.",
    },
    "mlx": {
        "label": "MLX worker",
        "backend": "mlx",
        "base_url_env": "IMAGE_GENERATION_MLX_BASE_URL",
        "model": "mlx-model",
        "steps": 4,
        "cfg_scale": 1.0,
        "sampler": "lcm",
        "recommended": False,
        "note": "Requires an OpenAI-compatible MLX image worker.",
    },
}


def get_image_profile(name: str) -> ImageProfile:
    return IMAGE_PROFILES.get(name, IMAGE_PROFILES["fast"])
