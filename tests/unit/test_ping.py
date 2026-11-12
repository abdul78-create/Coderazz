"""Unit tests for /api/v1/ping endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_api_v1_ping():
    """Verify API v1 ping returns pong and valid metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"
        assert data["app"] == "CodeRazz"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
