"""Aggregate API routers into root v1 router."""

from backend.app.api.v1 import (
    analytics,
    annotations,
    auth,
    classes,
    hints,
    ping,
    problems,
    submissions,
)
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(ping.router)
api_router.include_router(auth.router)
api_router.include_router(problems.router)
api_router.include_router(submissions.router)
api_router.include_router(hints.router)
api_router.include_router(classes.router)
api_router.include_router(analytics.router)
api_router.include_router(annotations.router)
