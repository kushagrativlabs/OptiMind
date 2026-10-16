from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OptiMind API"
    api_prefix: str = "/api/v1"
    database_url: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_keep_alive: str = "30m"
    ollama_num_ctx: int = 4096
    ollama_num_predict: int = 3000
    image_generation_enabled: bool = False
    image_generation_base_url: str = "http://localhost:1234"
    image_generation_model: str = "lcm-ssd-1b-q4"
    image_generation_size: str = "512x512"
    image_generation_steps: int = 4
    image_generation_cfg_scale: float = 1.0
    image_generation_sampler: str = "lcm"
    web_search_enabled: bool = False
    searxng_base_url: str = "http://localhost:8080"
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
