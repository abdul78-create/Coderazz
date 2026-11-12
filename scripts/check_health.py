"""Script to check CodeRazz backend health and API connectivity."""

import sys
import asyncio
from httpx import AsyncClient


async def check_api(base_url: str = "http://localhost:8000"):
    print(f"Connecting to CodeRazz backend at {base_url}...")
    try:
        async with AsyncClient(base_url=base_url, timeout=5.0) as client:
            # 1. Health check
            health_res = await client.get("/health")
            print(f"[Health Check] Status: {health_res.status_code}")
            print(health_res.json())

            # 2. Ping check
            ping_res = await client.get("/api/v1/ping")
            print(f"[Ping Check] Status: {ping_res.status_code}")
            print(ping_res.json())

            print("\nBackend is healthy and operational!")
    except Exception as e:
        print(f"Failed to connect to backend: {e}")
        sys.exit(1)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    asyncio.run(check_api(url))

