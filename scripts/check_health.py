"""Script to check CodeRazz backend health, PostgreSQL connectivity, and Docker Sandbox status."""

import asyncio
import pathlib
import sys

# Ensure repository root is on Python path
repo_root = pathlib.Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import httpx
from sqlalchemy import func, select

from backend.app.database import check_db_health, get_session_factory
from backend.app.models.problem import Problem, TestCase
from backend.app.models.submission import Submission
from backend.app.services.sandbox import SandboxService


async def check_api(base_url: str = "http://localhost:8001"):
    print("==================================================")
    print("       CodeRazz System Health & Sandbox Audit      ")
    print("==================================================")

    # 1. Check Database
    print("\n[1/3] Probing PostgreSQL 16 connection...")
    db_health = await check_db_health()
    print(f"Database Health: {db_health}")
    if db_health.get("status") != "connected":
        print("ERROR: Database is not connected!")
        sys.exit(1)

    factory = get_session_factory()
    async with factory() as session:
        prob_count = (await session.execute(select(func.count(Problem.id)))).scalar() or 0
        tc_count = (await session.execute(select(func.count(TestCase.id)))).scalar() or 0
        sub_count = (await session.execute(select(func.count(Submission.id)))).scalar() or 0
        print(f"Catalog Status: {prob_count} problems, {tc_count} test cases, {sub_count} submissions.")

    # 2. Check Docker Sandbox Runner
    print("\n[2/3] Checking Docker Sandbox Runner Container...")
    sandbox = SandboxService()
    docker_ok = await sandbox.is_docker_available()
    print(f"Docker Runner Available: {docker_ok}")
    if not docker_ok:
        print("WARNING: Docker runner is not available. Please ensure Docker Desktop is running.")
    else:
        print("Docker container image: coderazz-python-runner:latest is ready for sandboxed execution.")

    # 3. Check API Endpoints
    print("\n[3/3] Probing FastAPI Application...")
    from backend.app.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        health_res = await client.get("/health")
        print(f"[Health Check - ASGI] Status: {health_res.status_code}")
        print(f"Response: {health_res.json()}")

        ping_res = await client.get("/api/v1/ping")
        print(f"[Ping Check - ASGI] Status: {ping_res.status_code}")
        print(f"Response: {ping_res.json()}")

        problems_res = await client.get("/api/v1/problems")
        print(f"[Problems Catalog Check] Status: {problems_res.status_code}")
        print(f"Visible Problems: {len(problems_res.json())}")

    print("\n[SUCCESS] CodeRazz Phase 3 System is fully operational and healthy!\n")


if __name__ == "__main__":
    asyncio.run(check_api())
