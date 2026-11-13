"""Concurrency and stress tests for CodeRazz Docker Sandbox Execution Service.

Fires 25 simultaneous container execution requests under load to verify:
1. Docker orchestrator isolation and concurrency handling.
2. Strict enforcement of memory ceiling (128 MB) and process limits (--pids-limit 32).
3. Zero HTTP 500 Internal Server Errors under burst load.
4. Guaranteed container lifecycle teardown with 0 orphan containers.
"""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.models.submission import SubmissionVerdict


async def _get_auth_headers(client: AsyncClient, email: str) -> dict[str, str]:
    """Register and login a test user to obtain Bearer authorization headers."""
    password = "SecurePassword#123"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Concurrency Test User",
            "role": "student",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_sandbox_25_concurrent_executions() -> None:
    """Stress test: 25 simultaneous container executions with mixed benign and hostile payloads."""
    transport = ASGITransport(app=app)
    user_email = f"stress_student_{uuid.uuid4().hex[:8]}@coderazz.org"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(client, user_email)

        # 1. Prepare 25 heterogeneous payloads
        payloads = []

        # 10 Benign compute payloads
        for i in range(10):
            benign_code = (
                f"import sys\n"
                f"val = int(sys.stdin.read().strip() or {i})\n"
                f"print(val * val)\n"
            )
            payloads.append({
                "type": "benign",
                "code": benign_code,
                "custom_input": str(i + 5),
                "expected_output": str((i + 5) ** 2),
            })

        # 4 Hostile: Process / Fork bomb attacks
        fork_code = (
            "import os, sys\n"
            "try:\n"
            "    for _ in range(50):\n"
            "        os.fork()\n"
            "    print('FORK_SUCCESS')\n"
            "except Exception as e:\n"
            "    print(f'FORK_CAUGHT: {type(e).__name__}')\n"
        )
        for _ in range(4):
            payloads.append({
                "type": "fork_bomb",
                "code": fork_code,
                "custom_input": "",
            })

        # 4 Hostile: Memory exhaustion (>128 MB)
        mem_code = (
            "chunks = []\n"
            "try:\n"
            "    for _ in range(25):\n"
            "        chunks.append(b'M' * (10 * 1024 * 1024))\n"
            "    print('ALLOC_SUCCESS')\n"
            "except MemoryError:\n"
            "    print('MEMORY_CAUGHT')\n"
        )
        for _ in range(4):
            payloads.append({
                "type": "memory_bomb",
                "code": mem_code,
                "custom_input": "",
            })

        # 4 Hostile: Infinite loop timeout
        loop_code = (
            "while True:\n"
            "    pass\n"
        )
        for _ in range(4):
            payloads.append({
                "type": "infinite_loop",
                "code": loop_code,
                "custom_input": "",
            })

        # 3 Logic error / Misconception payloads
        a1_code = (
            "import sys\n"
            "arr = [10, 20, 30]\n"
            "for i in range(len(arr) + 1):\n"
            "    x = arr[i]\n"
        )
        for _ in range(3):
            payloads.append({
                "type": "logic_error",
                "code": a1_code,
                "custom_input": "",
            })

        assert len(payloads) == 25, f"Expected exactly 25 payloads, got {len(payloads)}"

        # 2. Fire 25 simultaneous requests
        async def _run_single(idx: int, p: dict):
            req_body = {"code": p["code"], "custom_input": p.get("custom_input", "")}
            res = await client.post("/api/v1/submissions/run", headers=headers, json=req_body)
            return idx, p["type"], res

        tasks = [_run_single(i, p) for i, p in enumerate(payloads)]
        results = await asyncio.gather(*tasks)

        # 3. Verify responses and isolation guarantees
        for idx, ptype, res in results:
            # Under no circumstances should an unhandled 500 be thrown
            assert res.status_code == 200, (
                f"Request #{idx} ({ptype}) failed with unexpected HTTP {res.status_code}: {res.text}"
            )
            data = res.json()

            if ptype == "benign":
                # Benign compute must succeed cleanly
                assert data["verdict"] == SubmissionVerdict.ACCEPTED.value, (
                    f"Benign request #{idx} failed: {data}"
                )
                assert data["stdout"].strip() == payloads[idx]["expected_output"], (
                    f"Benign request #{idx} output mismatch: {data['stdout']}"
                )

            elif ptype == "fork_bomb":
                # Fork bomb must never report unhindered fork proliferation
                assert "FORK_SUCCESS" not in data.get("stdout", "")
                assert data["verdict"] in [
                    SubmissionVerdict.RUNTIME_ERROR.value,
                    SubmissionVerdict.SANDBOX_ERROR.value,
                    SubmissionVerdict.ACCEPTED.value,  # If OS caught exception and printed FORK_CAUGHT
                ]

            elif ptype == "memory_bomb":
                # Memory explosion must be bounded by 128 MB
                assert "ALLOC_SUCCESS" not in data.get("stdout", "")
                assert (
                    "MEMORY_CAUGHT" in data.get("stdout", "")
                    or data["verdict"] in [
                        SubmissionVerdict.MEMORY_LIMIT_EXCEEDED.value,
                        SubmissionVerdict.RUNTIME_ERROR.value,
                    ]
                )

            elif ptype == "infinite_loop":
                # Infinite loops must hit timeout and be killed
                assert data["verdict"] == SubmissionVerdict.TIME_LIMIT_EXCEEDED.value, (
                    f"Infinite loop request #{idx} did not timeout: {data}"
                )

            elif ptype == "logic_error":
                # Runtime error / index out of bounds must be reported
                assert data["verdict"] == SubmissionVerdict.RUNTIME_ERROR.value, (
                    f"Logic error request #{idx} verdict was not RUNTIME_ERROR: {data}"
                )

        # 4. Zero Orphan Container Verification
        # Wait a grace second for any async subprocess reaper to complete
        await asyncio.sleep(1.0)

        check_proc = await asyncio.create_subprocess_exec(
            "docker",
            "ps",
            "--filter",
            "name=coderazz-exec",
            "--format",
            "{{.ID}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await check_proc.communicate()
        running_orphans = [line.strip() for line in out.decode().splitlines() if line.strip()]
        assert len(running_orphans) == 0, (
            f"Concurrency stress test left {len(running_orphans)} running orphan container(s): {running_orphans}"
        )
