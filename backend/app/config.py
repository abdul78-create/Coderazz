"""Application configuration module using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings and environment configuration for CodeRazz."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    ENV: str = "development"
    APP_NAME: str = "CodeRazz"
    APP_PORT: int = 8000
    FRONTEND_PORT: int = 3000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = "coderazz_dev_secret_key_change_in_production_32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_URL: str = (
        "postgresql+psycopg://coderazz_user:coderazz_local_password@localhost:5432/coderazz_db"
    )
    FALLBACK_SQLITE_URL: str = "sqlite+aiosqlite:///./coderazz_dev.db"
    FORCE_SQLITE_DEV: bool = False

    # Execution Sandbox
    SANDBOX_MODE: str = "docker"
    SANDBOX_TIMEOUT_SECONDS: float = 3.0
    SANDBOX_MEM_LIMIT_MB: int = 128
    SANDBOX_CPU_LIMIT: float = 1.0
    SANDBOX_MAX_OUTPUT_BYTES: int = 65536

    # Optional Local LLM (Ollama)
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-coder:6.7b"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
