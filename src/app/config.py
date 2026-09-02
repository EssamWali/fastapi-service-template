"""Application settings, loaded from the environment once at import time."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Every knob the service has. Nothing reads os.environ directly except this class."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["local", "ci", "staging", "prod"] = "local"
    log_level: str = "INFO"

    # Comma-separated in the environment, a list in the code.
    #
    # NoDecode is load-bearing: without it pydantic-settings tries json.loads() on
    # any complex-typed field read from the environment, so APP_API_KEYS=a,b blows up
    # before the validator below ever runs. It only shows up when you boot the real
    # process - tests that pass a list directly never touch the env source.
    api_keys: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["dev-key-change-me"])

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_echo: bool = False

    # Empty means "no Redis" - the cache falls back to an in-process dict.
    redis_url: str = ""
    cache_ttl_seconds: int = 60

    @field_validator("api_keys", mode="before")
    @classmethod
    def _split_keys(cls, v: object) -> object:
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is parsed once. Call .cache_clear() in tests."""
    return Settings()
