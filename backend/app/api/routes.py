"""Aggregate API routers into root v1 router."""

from backend.app.api.v1 import ping
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(ping.router)
