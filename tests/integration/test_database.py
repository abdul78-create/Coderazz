"""Integration tests verifying PostgreSQL async engine, sessions, and explicit modes."""

import pytest
from sqlalchemy import text

from backend.app.config import get_settings
from backend.app.database import (
    check_db_health,
    get_engine,
    get_session_factory,
    reset_engine,
)


@pytest.mark.asyncio
async def test_postgres_async_connection():
    """Verify raw asyncpg can connect to the running PostgreSQL container on port 5433."""
    import asyncpg

    settings = get_settings()
    conn = await asyncpg.connect(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        timeout=5,
    )
    try:
        version = await conn.fetchval("SELECT version()")
        assert "PostgreSQL 16" in version
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_async_sqlalchemy_session_select_one():
    """Verify FastAPI's async SQLAlchemy session executes SELECT 1 against PostgreSQL."""
    factory = get_session_factory()
    async with factory() as session:
        res = await session.execute(text("SELECT 1"))
        assert res.scalar() == 1


@pytest.mark.asyncio
async def test_active_dialect_is_postgresql():
    """Verify active engine dialect and driver are strictly postgresql and asyncpg."""
    engine = get_engine()
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "asyncpg"


@pytest.mark.asyncio
async def test_sqlite_mode_works_independently(monkeypatch, tmp_path):
    """Verify explicit SQLite mode works as an independent local development option."""
    test_db_file = tmp_path / "test_coderazz.db"
    sqlite_url = f"sqlite+aiosqlite:///{test_db_file}"

    # Temporarily switch settings to SQLite mode
    monkeypatch.setattr(get_settings(), "DB_MODE", "sqlite")
    monkeypatch.setattr(get_settings(), "SQLITE_URL", sqlite_url)

    reset_engine()
    try:
        engine = get_engine()
        assert engine.dialect.name == "sqlite"
        assert engine.dialect.driver == "aiosqlite"

        factory = get_session_factory()
        async with factory() as session:
            res = await session.execute(text("SELECT 1"))
            assert res.scalar() == 1

        health = await check_db_health()
        assert health["status"] == "connected"
        assert health["mode"] == "sqlite"
        assert health["dialect"] == "sqlite"
        assert health["driver"] == "aiosqlite"
    finally:
        # Restore PostgreSQL engine
        reset_engine()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_postgres_connection_failure_reported_honestly(monkeypatch):
    """Verify PostgreSQL connection failure is reported honestly without silent fallback."""
    # Point to an unallocated port to simulate failure
    bad_url = "postgresql+asyncpg://coderazz_user:coderazz_local_password@localhost:5499/coderazz_db"
    monkeypatch.setattr(get_settings(), "DATABASE_URL", bad_url)
    monkeypatch.setattr(get_settings(), "DB_MODE", "postgresql")

    reset_engine()
    try:
        health = await check_db_health()
        assert health["status"] == "disconnected"
        assert health["mode"] == "postgresql"
        assert health["dialect"] == "postgresql"
        assert health["driver"] == "asyncpg"
        assert health["error"] is not None
        # Must NOT silently report connected or change to sqlite
        assert health["version"] is None
    finally:
        reset_engine()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_no_silent_fallback_on_failure(monkeypatch):
    """Verify that an asyncpg connection failure does not silently mask as SQLite."""
    bad_url = "postgresql+asyncpg://invalid_user:invalid_pwd@localhost:5433/coderazz_db"
    monkeypatch.setattr(get_settings(), "DATABASE_URL", bad_url)
    monkeypatch.setattr(get_settings(), "DB_MODE", "postgresql")

    reset_engine()
    try:
        engine = get_engine()
        assert engine.dialect.name == "postgresql"
        # Attempting query raises error rather than silently delegating to SQLite
        from sqlalchemy.exc import DBAPIError
        with pytest.raises(DBAPIError):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    finally:
        reset_engine()
        get_settings.cache_clear()
