"""Main FastAPI application entry point for CodeRazz."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from backend.app.api.routes import api_router
from backend.app.config import get_settings
from backend.app.database import check_db_health
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("coderazz.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    settings = get_settings()
    logger.info("Initializing %s in %s environment...", settings.APP_NAME, settings.ENV)

    # Validate database connectivity at startup
    db_report = await check_db_health()
    logger.info("Database connectivity report: %s", db_report)

    yield

    logger.info("Shutting down %s...", settings.APP_NAME)


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "A Misconception-Aware Programming Tutor backend API. "
            "Identifies pedagogical misconceptions, provides progressive hints, "
            "and drives class-level learning analytics with a ₹0 budget."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(api_router)

    # Health check response model
    class DatabaseStatus(BaseModel):
        status: str
        dialect: str
        target: str
        fallback_active: bool
        postgres_container_verified: bool | None = None
        postgres_version: str | None = None
        notice: str | None = None
        error: str | None = None

    class HealthResponse(BaseModel):
        status: str = Field(default="healthy")
        app: str
        environment: str
        version: str
        database: DatabaseStatus

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        """Root health check endpoint returning system and database connectivity status."""
        db_status = await check_db_health()
        overall_status = "healthy" if db_status.get("status") == "connected" else "degraded"

        return HealthResponse(
            status=overall_status,
            app=settings.APP_NAME,
            environment=settings.ENV,
            version="0.1.0",
            database=DatabaseStatus(**db_status),
        )

    @app.get("/", tags=["Root"])
    async def root_index() -> dict:
        """Root informational greeting."""
        return {
            "app": settings.APP_NAME,
            "tagline": "Don't just fix the code. Understand the thinking behind it.",
            "version": "0.1.0",
            "docs": "/docs" if settings.DEBUG else "disabled",
            "health": "/health",
            "api_ping": "/api/v1/ping",
        }

    return app


app = create_application()
