"""Database connection management and session factory."""

import logging
from typing import AsyncGenerator

from backend.app.config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

logger = logging.getLogger("coderazz.database")


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_factory() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create async engine and session factory according to explicit DB_MODE configuration.

    No silent fallback:
    - If DB_MODE is 'postgresql', strictly initialize with asyncpg.
    - If DB_MODE is 'sqlite', strictly initialize with aiosqlite.
    """
    settings = get_settings()
    db_url = settings.get_effective_db_url()

    logger.info("Initializing async database engine in '%s' mode: %s", settings.DB_MODE, db_url)

    connect_args = {}
    if settings.DB_MODE == "sqlite":
        connect_args["check_same_thread"] = False

    engine = create_async_engine(
        db_url,
        echo=settings.DEBUG and settings.ENV == "development",
        future=True,
        poolclass=NullPool,
        connect_args=connect_args,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine, session_factory


def get_engine() -> AsyncEngine:
    """Retrieve or initialize the active AsyncEngine."""
    global _engine, _session_factory
    if _engine is None:
        _engine, _session_factory = create_engine_and_factory()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve or initialize the active async session factory."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine, _session_factory = create_engine_and_factory()
    return _session_factory


def reset_engine() -> None:
    """Reset the engine singleton (used in tests or dynamic re-configuration)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> dict:
    """Verify active async database connectivity and return health report."""
    settings = get_settings()
    engine = get_engine()

    try:
        async with engine.connect() as conn:
            # Execute probe query
            res = await conn.execute(text("SELECT 1"))
            val = res.scalar()

            # Retrieve database engine version string
            if engine.dialect.name == "postgresql":
                ver_res = await conn.execute(text("SELECT version()"))
                db_version = ver_res.scalar()
            else:
                ver_res = await conn.execute(text("SELECT sqlite_version()"))
                db_version = f"SQLite {ver_res.scalar()}"

            return {
                "status": "connected" if val == 1 else "unhealthy",
                "mode": settings.DB_MODE,
                "dialect": engine.dialect.name,
                "driver": engine.dialect.driver,
                "version": db_version,
                "error": None,
            }
    except Exception as err:
        logger.error(
            "Database connectivity check failed in '%s' mode: %s",
            settings.DB_MODE,
            err,
        )
        return {
            "status": "disconnected",
            "mode": settings.DB_MODE,
            "dialect": engine.dialect.name,
            "driver": engine.dialect.driver,
            "version": None,
            "error": str(err),
        }
