"""Unit tests for /health and root endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_root_index():
    """Verify root information endpoint responds with 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "CodeRazz"
        assert "tagline" in data
        assert data["version"] == "0.1.0"
        assert data["health"] == "/health"
        assert data["api_ping"] == "/api/v1/ping"


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify health check endpoint returns status and database report with PostgreSQL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "CodeRazz"
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "connected"
        assert data["database"]["mode"] == "postgresql"
        assert data["database"]["dialect"] == "postgresql"
        assert data["database"]["driver"] == "asyncpg"
        assert "PostgreSQL 16" in data["database"]["version"]
        assert data["database"]["error"] is None
