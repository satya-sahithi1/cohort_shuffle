"""
config.py — Application settings loaded from environment variables.

All configuration lives here. Other modules import get_settings() and
never read os.environ directly.

Usage:
    from app.config import get_settings
    settings = get_settings()
    print(settings.database_url)

Environment variables are read from a .env file at the backend root.
Copy .env.example to .env and fill in the values before running.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────
    # Full async PostgreSQL URL.
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cohort_shuffle"

    # ── Auth ──────────────────────────────────────────────────────────────
    # Secret key used to sign JWT tokens. Change this in production.
    secret_key: str = "dev-secret-key-change-in-production"
    # Algorithm used for JWT signing.
    jwt_algorithm: str = "HS256"
    # Token expiry in minutes.
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "Cohort Shuffle"
    debug: bool = True
    # Allowed origins for CORS (frontend dev server).
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    lru_cache means this is only instantiated once per process —
    subsequent calls return the same object.
    """
    return Settings()
