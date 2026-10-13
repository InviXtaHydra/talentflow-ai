from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MatchingWeights(BaseSettings):
    """Default weights of the match score components (see docs/ai-matching.md).

    They are relative weights: components that cannot be evaluated are left out and the
    remaining weights are renormalized, so they don't have to add up to exactly 1.
    """

    model_config = SettingsConfigDict(env_prefix="MATCH_WEIGHT_", extra="ignore")

    skills: float = 0.35
    experience: float = 0.25
    role: float = 0.20
    qualifications: float = 0.10
    preferences: float = 0.10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "TalentFlow AI"
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:3300"
    backend_url: str = "http://localhost:8300"
    cors_origins: str = "http://localhost:3300"

    database_url: str = "postgresql+psycopg://talentflow:talentflow@localhost:5436/talentflow"

    secret_key: str = Field(default="dev-insecure-secret-change-me", min_length=16)
    session_ttl_hours: int = 336
    cookie_domain: str | None = None

    ai_provider: Literal["ollama", "openai", "none", "fake"] = "ollama"
    ai_model: str = "qwen3:8b"
    ai_base_url: str = "http://host.docker.internal:11434"
    ai_api_key: str | None = None
    ai_timeout_seconds: float = 300
    embedding_provider: Literal["ollama", "openai", "fake", ""] = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    storage_dir: str = "/data/storage"
    max_upload_mb: float = 5
    max_logo_mb: float = 1

    email_backend: Literal["smtp", "console", "memory"] = "smtp"
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False
    email_from: str = "TalentFlow AI <no-reply@talentflow.local>"

    inactive_account_retention_days: int = 0
    operational_log_retention_days: int = 90

    @field_validator("cookie_domain", "ai_api_key", "smtp_username", "smtp_password", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def max_logo_bytes(self) -> int:
        return int(self.max_logo_mb * 1024 * 1024)

    @property
    def ai_enabled(self) -> bool:
        return self.ai_provider not in ("none",)

    @property
    def embeddings_enabled(self) -> bool:
        return bool(self.embedding_provider)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.ai_provider == "fake" and settings.app_env != "test":
        raise RuntimeError("AI_PROVIDER=fake is only allowed when APP_ENV=test")
    if settings.is_production and settings.secret_key.startswith("dev-insecure"):
        raise RuntimeError("Set a real SECRET_KEY in production")
    return settings


@lru_cache
def get_matching_weights() -> MatchingWeights:
    return MatchingWeights()
