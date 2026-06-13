"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe application configuration sourced from the environment / ``.env``.

    All values are validated at import time, so missing or invalid configuration
    fails fast on boot rather than on the first request.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # External API credentials
    openweather_api_key: str = Field(..., min_length=10)
    groq_api_key: str = Field(..., min_length=10)

    # LLM configuration
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1500, ge=100, le=8000)
    llm_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)

    # Weather API configuration
    weather_timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    weather_units: Literal["metric", "imperial"] = "metric"

    # Cache configuration
    cache_ttl_seconds: int = Field(default=600, ge=0, le=86400)  # 10 min default

    # Concurrency limits
    max_concurrent_llm_calls: int = Field(default=10, ge=1, le=100)
    max_concurrent_weather_calls: int = Field(default=20, ge=1, le=100)

    # Per-IP rate limiting on the expensive LLM endpoints
    rate_limit_enabled: bool = True
    rate_limit: str = "20/minute"

    # CORS. `NoDecode` stops pydantic-settings from JSON-decoding the env var
    # before our validator runs — without it, a plain/comma-separated value like
    # "https://a.com,https://b.com" raises a JSON parse error at startup.
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        """Accept a comma-separated string (or a single origin) from the env var."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton. Validates on first access."""
    return Settings()  # type: ignore[call-arg]
