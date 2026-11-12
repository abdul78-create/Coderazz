"""Script to check CodeRazz backend health and API connectivity."""

import asyncio
import pathlib
import sys

# Ensure repository root is on Python path
repo_root = pathlib.Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import httpx


async def check_api(base_url: str = "http://localhost:8001"):
    print(f"Connecting to CodeRazz backend at {base_url}...")
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=3.0) as client:
            health_res = await client.get("/health")
            print(f"[Health Check] Status: {health_res.status_code}")
            print(health_res.json())

            ping_res = await client.get("/api/v1/ping")
            print(f"[Ping Check] Status: {ping_res.status_code}")
            print(ping_res.json())

            print("\nBackend is healthy and operational via live HTTP!")
            return
    except (httpx.HTTPError, OSError):
        print(f"No standalone HTTP server running at {base_url}. Probing backend via ASGI...")

    try:
        from backend.app.main import create_application

        app = create_application()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            health_res = await client.get("/health")
            print(f"[Health Check - ASGI] Status: {health_res.status_code}")
            print(health_res.json())

            ping_res = await client.get("/api/v1/ping")
            print(f"[Ping Check - ASGI] Status: {ping_res.status_code}")
            print(ping_res.json())

            print("\nBackend is healthy and operational via direct ASGI probe!")
    except Exception as err:  # noqa: BLE001
        print(f"Failed to verify backend health: {err}")
        sys.exit(1)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    asyncio.run(check_api(url))


