"""Unit tests for application configuration."""

from backend.app.config import Settings, get_settings


def test_settings_defaults():
    """Verify default configuration values adhere to zero-cost and FOSS policies."""
    settings = get_settings()
    assert settings.APP_NAME == "CodeRazz"
    assert settings.APP_PORT == 8000
    assert settings.FRONTEND_PORT == 3000
    assert "postgresql" in settings.DATABASE_URL
    assert "sqlite" in settings.FALLBACK_SQLITE_URL
    assert settings.OLLAMA_ENABLED is False  # Zero cost, optional local LLM only


def test_settings_custom_instance():
    """Verify settings can be instantiated with custom values."""
    custom = Settings(
        APP_NAME="CodeRazz-Test",
        FORCE_SQLITE_DEV=True,
        SANDBOX_TIMEOUT_SECONDS=5.0,
    )
    assert custom.APP_NAME == "CodeRazz-Test"
    assert custom.FORCE_SQLITE_DEV is True
    assert custom.SANDBOX_TIMEOUT_SECONDS == 5.0
