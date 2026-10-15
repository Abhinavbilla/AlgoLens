"""Runtime configuration, read from ALGOLENS_* environment variables (and .env)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALGOLENS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://algolens:algolens@localhost:5432/algolens"
    sandbox_socket: str = "/run/sandbox/sandbox.sock"
    # The repo's library/ folder when run from a checkout; the image sets /app/library.
    library_dir: Path = Path(__file__).resolve().parents[2] / "library"

    # One model per pipeline role, as "provider:model" (see algolens/ai/client.py). API keys
    # are read from the environment: GEMINI_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY, ...
    # Brute B must differ from Brute A (§6.2); by default it's another company's model.
    model_parse: str = "gemini:gemini-3.8-flash"
    model_brute_a: str = "gemini:gemini-3.8-flash"
    model_brute_b: str = "groq:openai/gpt-oss-120b"
    model_approaches: str = "gemini:gemini-3.8-flash"
    model_checker: str = "gemini:gemini-3.8-flash"
    model_repair: str = "gemini:gemini-3.8-flash"
    model_narration: str = "gemini:gemini-3.8-flash"
    # The thought-process explanation; empty means "same model as narration".
    model_explain: str = ""

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
