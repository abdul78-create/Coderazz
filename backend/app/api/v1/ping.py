"""Ping diagnostic endpoint for v1 API."""

from datetime import datetime, timezone

from backend.app.config import get_settings
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["Diagnostics"])


class PingResponse(BaseModel):
    """Schema for ping diagnostic response."""
    message: str = Field(default="pong", description="Response echo")
    app: str = Field(..., description="Application name")
    version: str = Field(default="0.1.0", description="API version")
    timestamp: datetime = Field(..., description="UTC timestamp of response")


@router.get("/ping", response_model=PingResponse, summary="API v1 ping test")
async def ping() -> PingResponse:
    """Diagnostic endpoint to verify API v1 connectivity."""
    settings = get_settings()
    return PingResponse(
        message="pong",
        app=settings.APP_NAME,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )
