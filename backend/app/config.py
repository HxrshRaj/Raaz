from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAAZ_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = f"sqlite:///{(BASE_DIR / 'raaz.db').as_posix()}"
    db_pool_size: int = 10
    redis_url: str | None = None

    jwt_secret: str = "dev-insecure-secret-change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allow_guest: bool = True
    metrics_token: str | None = None

    # LLM -------------------------------------------------------------
    llm_provider: Literal["none", "anthropic", "openai"] = "none"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_timeout_s: float = 20.0
    llm_max_retries: int = 2
    llm_max_output_tokens: int = 450
    conversation_token_budget: int = 40_000
    llm_cost_per_1k_in_usd: float = 0.0  # set to track *estimated* cost; 0 = not tracked
    llm_cost_per_1k_out_usd: float = 0.0

    # Limits ----------------------------------------------------------
    rate_limit_per_min: int = 240
    llm_rate_limit_per_min: int = 30
    agent_runs_per_hour: int = 20
    agent_max_iterations: int = 12
    agent_timeout_s: float = 25.0

    # ML --------------------------------------------------------------
    artifacts_dir: str = str(BASE_DIR / "artifacts")
    mlflow_tracking_uri: str | None = None
    ml_workbench_enabled: bool | None = None  # default: on in dev/test, OFF in prod unless explicitly enabled

    @property
    def workbench_on(self) -> bool:
        return self.ml_workbench_enabled if self.ml_workbench_enabled is not None else self.env != "prod"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_for_runtime(self) -> None:
        if self.env == "prod":
            weak = self.jwt_secret.startswith("dev-insecure") or "CHANGE_ME" in self.jwt_secret or len(self.jwt_secret) < 32
            if weak:
                raise RuntimeError("RAAZ_JWT_SECRET must be a strong random secret (>= 32 chars) when RAAZ_ENV=prod")


@lru_cache
def get_settings() -> Settings:
    return Settings()
