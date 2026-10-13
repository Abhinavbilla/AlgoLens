"""Runtime configuration, read from ALGOLENS_* environment variables (and .env)."""

from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALGOLENS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://algolens:algolens@localhost:5432/algolens"

    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ALGOLENS_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    )

    # One model per pipeline role (plan §6). Brute B must differ from Brute A (§6.2).
    model_parse: str = "claude-sonnet-5-5"
    model_brute_a: str = "claude-sonnet-5-5"
    model_brute_b: str = "claude-opus-5-5"
    model_approaches: str = "claude-sonnet-5-5"
    model_checker: str = "claude-sonnet-5-5"
    model_repair: str = "claude-opus-5-5"
    model_narration: str = "claude-sonnet-5-5"

    # Per-problem AI budget, input + output tokens across all calls (plan §6.4).
    max_tokens_per_problem: int = Field(default=200_000, gt=0)
    max_repair_rounds: int = Field(default=2, ge=0)

    worker_poll_seconds: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def _brute_forces_use_different_models(self) -> "Settings":
        if self.model_brute_a == self.model_brute_b:
            raise ValueError(
                "ALGOLENS_MODEL_BRUTE_A and ALGOLENS_MODEL_BRUTE_B must be different models, "
                "so the two reference solutions stay independent"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
