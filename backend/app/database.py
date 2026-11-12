"""Database connection management and session factory."""

import logging
from typing import AsyncGenerator, Tuple

from backend.app.config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("coderazz.database")


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_active_dialect: str = "unknown"


def create_engine_and_factory() -> Tuple[AsyncEngine, async_sessionmaker[AsyncSession], str]:
    """Create async engine with automatic SQLite fallback if PostgreSQL is offline."""
    global _engine, _session_factory, _active_dialect
    settings = get_settings()

    if settings.FORCE_SQLITE_DEV:
        logger.info("Explicit FORCE_SQLITE_DEV flag set. Using SQLite database.")
        db_url = settings.FALLBACK_SQLITE_URL
    else:
        db_url = settings.DATABASE_URL

    try:
        # Note: connect_args={'check_same_thread': False} if sqlite
        connect_args = {}
        if "sqlite" in db_url:
            connect_args["check_same_thread"] = False

        engine = create_async_engine(
            db_url,
            echo=settings.DEBUG and settings.ENV == "development",
            future=True,
            connect_args=connect_args,
        )
        dialect_name = "postgresql" if "postgresql" in db_url else "sqlite"
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        return engine, session_factory, dialect_name
    except Exception as exc:
        logger.warning(
            "Primary database connection setup failed (%s). Falling back to SQLite development DB.",
            exc,
        )
        fallback_engine = create_async_engine(
            settings.FALLBACK_SQLITE_URL,
            echo=False,
            connect_args={"check_same_thread": False},
        )
        fallback_factory = async_sessionmaker(
            bind=fallback_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        return fallback_engine, fallback_factory, "sqlite"


def get_engine() -> AsyncEngine:
    """Retrieve or initialize the active AsyncEngine."""
    global _engine, _session_factory, _active_dialect
    if _engine is None:
        _engine, _session_factory, _active_dialect = create_engine_and_factory()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve or initialize the active async session factory."""
    global _engine, _session_factory, _active_dialect
    if _session_factory is None:
        _engine, _session_factory, _active_dialect = create_engine_and_factory()
    return _session_factory


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
    """Verify database connectivity and return health report."""
    global _active_dialect, _engine, _session_factory
    engine = get_engine()
    settings = get_settings()

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            return {
                "status": "connected" if val == 1 else "unhealthy",
                "dialect": _active_dialect,
                "target": "postgresql" if not settings.FORCE_SQLITE_DEV else "sqlite",
                "fallback_active": _active_dialect == "sqlite",
            }
    except Exception as err:
        # If PostgreSQL failed on connect, switch runtime fallback to SQLite
        if _active_dialect != "sqlite":
            logger.warning(
                "PostgreSQL health check failed (%s). Activating SQLite local-dev fallback.",
                err,
            )
            _engine = create_async_engine(
                settings.FALLBACK_SQLITE_URL,
                echo=False,
                connect_args={"check_same_thread": False},
            )
            _session_factory = async_sessionmaker(
                bind=_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            _active_dialect = "sqlite"

            try:
                async with _engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    val = result.scalar()
                    return {
                        "status": "connected" if val == 1 else "unhealthy",
                        "dialect": "sqlite",
                        "target": "postgresql",
                        "fallback_active": True,
                        "notice": (
                            "PostgreSQL unavailable; using local development SQLite database."
                        ),
                    }
            except Exception as fallback_err:
                return {
                    "status": "disconnected",
                    "error": str(fallback_err),
                    "dialect": "none",
                }

        return {
            "status": "disconnected",
            "error": str(err),
            "dialect": _active_dialect,
        }
