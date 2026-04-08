"""Application configuration loaded from environment variables.

All settings are read from environment variables (and `.env` if present)
via pydantic-settings. There is a single `settings` instance used
throughout the app.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Mistral ---
    mistral_api_key: str
    mistral_model: str = "mistral-large-latest"
    mistral_embed_model: str = "mistral-embed"

    # --- Database (psycopg3 DSN) ---
    # Example: postgresql+psycopg://bnp:bnp@db:5432/bnp
    database_url: str = "postgresql+psycopg://bnp:bnp@localhost:5432/bnp"

    # --- CORS ---
    frontend_url: str = "http://localhost:5173"

    # --- Misc ---
    log_level: str = "INFO"

    # --- Agent ---
    agent_recursion_limit: int = 8  # ~4 LLM iterations max


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
