"""Unit tests for application configuration."""

from backend.app.config import Settings, get_settings


def test_settings_defaults():
    """Verify default configuration values adhere to zero-cost and FOSS policies."""
    settings = get_settings()
    assert settings.APP_NAME == "CodeRazz"
    assert settings.APP_PORT in (8000, 8001)
    assert settings.FRONTEND_PORT == 3000
    assert settings.DB_MODE == "postgresql"
    assert "postgresql+asyncpg" in settings.DATABASE_URL
    assert "sqlite+aiosqlite" in settings.SQLITE_URL
    assert settings.OLLAMA_ENABLED is False  # Zero cost, optional local LLM only


def test_settings_custom_instance():
    """Verify settings can be instantiated with custom values."""
    custom = Settings(
        APP_NAME="CodeRazz-Test",
        DB_MODE="sqlite",
        SANDBOX_TIMEOUT_SECONDS=5.0,
    )
    assert custom.APP_NAME == "CodeRazz-Test"
    assert custom.DB_MODE == "sqlite"
    assert custom.SANDBOX_TIMEOUT_SECONDS == 5.0
    assert "sqlite" in custom.get_effective_db_url()
