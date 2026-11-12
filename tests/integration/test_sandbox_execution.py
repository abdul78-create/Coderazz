"""Integration & Security tests for CodeRazz Docker Sandbox Execution Service.

Validates normal execution, full submission grading, cross-student RBAC access controls,
and hostile code security containment (infinite loops, memory bombs, network attempts,
filesystem writes, output floods, and zero orphaned containers).
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.models.submission import SubmissionVerdict
from backend.app.services.sandbox import SandboxService

TWO_SUM_CORRECT_CODE = """import sys

def solve():
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        return
    nums = list(map(int, lines[0].split()))
    target = int(lines[1].strip())
    
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            print(f"{seen[complement]} {i}")
            return
        seen[num] = i

if __name__ == "__main__":
    solve()
"""

TWO_SUM_WRONG_CODE = """import sys

def solve():
    print("0 0")

if __name__ == "__main__":
    solve()
"""

SYNTAX_ERROR_CODE = """def solve(
    print("Broken syntax"
"""


async def _get_auth_headers(client: AsyncClient, email: str, password: str, role: str) -> dict[str, str]:
    """Helper to register and login a user, returning Authorization headers."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": f"User {role}", "role": role},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_interactive_run_accepted():
    """Verify interactive code run against problem sample cases returns ACCEPTED."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_run_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        prob_res = await client.get("/api/v1/problems/two-sum")
        assert prob_res.status_code == 200
        problem_id = prob_res.json()["id"]

        run_res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": TWO_SUM_CORRECT_CODE,
                "problem_id": problem_id,
            },
        )
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["verdict"] == SubmissionVerdict.ACCEPTED.value
        assert data["test_cases_passed"] == data["total_test_cases"]
        assert data["test_cases_passed"] >= 2
        assert len(data["test_cases"]) >= 2
        for tc in data["test_cases"]:
            assert tc["passed"] is True
            assert tc["verdict"] == SubmissionVerdict.ACCEPTED.value


@pytest.mark.asyncio
async def test_interactive_run_wrong_answer():
    """Verify interactive code run producing incorrect output returns WRONG_ANSWER."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_wrong_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        prob_res = await client.get("/api/v1/problems/two-sum")
        problem_id = prob_res.json()["id"]

        run_res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": TWO_SUM_WRONG_CODE,
                "problem_id": problem_id,
            },
        )
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["verdict"] == SubmissionVerdict.WRONG_ANSWER.value
        assert data["test_cases_passed"] == 0
        assert data["test_cases"][0]["passed"] is False


@pytest.mark.asyncio
async def test_interactive_run_syntax_error():
    """Verify syntax error is detected and classified with compilation error verdict."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_syn_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        run_res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": SYNTAX_ERROR_CODE,
                "custom_input": "1 2\n3",
            },
        )
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["verdict"] in (
            SubmissionVerdict.COMPILATION_ERROR.value,
            SubmissionVerdict.RUNTIME_ERROR.value,
        )
        assert "SyntaxError" in data["stderr"]


@pytest.mark.asyncio
async def test_interactive_run_custom_input():
    """Verify custom stdin input execution when problem_id is omitted."""
    transport = ASGITransport(app=app)
    custom_code = "import sys\nprint('Hello ' + sys.stdin.read().strip())"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_cust_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        run_res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": custom_code,
                "custom_input": "CodeRazz",
            },
        )
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["verdict"] == SubmissionVerdict.ACCEPTED.value
        assert "Hello CodeRazz" in data["stdout"]


@pytest.mark.asyncio
async def test_submission_and_grading_accepted():
    """Verify full grading submission against all sample and hidden test cases."""
    transport = ASGITransport(app=app)
    student_email = f"grade_{uuid.uuid4().hex[:6]}@coderazz.edu"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(client, student_email, "StudentPass#123", "student")

        prob_res = await client.get("/api/v1/problems/two-sum")
        problem_id = prob_res.json()["id"]

        sub_res = await client.post(
            "/api/v1/submissions",
            headers=headers,
            json={
                "problem_id": problem_id,
                "code": TWO_SUM_CORRECT_CODE,
                "language": "python",
            },
        )
        assert sub_res.status_code == 201
        data = sub_res.json()
        assert data["verdict"] == SubmissionVerdict.ACCEPTED.value
        assert data["status"] == "COMPLETED"
        assert data["test_cases_passed"] == data["total_test_cases"]
        assert data["total_test_cases"] >= 4  # 2 samples + hidden cases


@pytest.mark.asyncio
async def test_submission_history_and_cross_student_rbac():
    """Verify submission history listing and cross-student RBAC privacy protection."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Student A submits code
        headers_a = await _get_auth_headers(
            client, f"stud_a_{uuid.uuid4().hex[:6]}@coderazz.edu", "PasswordA#123", "student"
        )
        prob_res = await client.get("/api/v1/problems/two-sum")
        problem_id = prob_res.json()["id"]

        sub_a = await client.post(
            "/api/v1/submissions",
            headers=headers_a,
            json={"problem_id": problem_id, "code": TWO_SUM_WRONG_CODE, "language": "python"},
        )
        sub_id = sub_a.json()["id"]

        # Student A can view their history
        hist_a = await client.get("/api/v1/submissions", headers=headers_a)
        assert hist_a.status_code == 200
        assert len(hist_a.json()) >= 1
        assert hist_a.json()[0]["id"] == sub_id

        # Student A can view their own submission details
        detail_a = await client.get(f"/api/v1/submissions/{sub_id}", headers=headers_a)
        assert detail_a.status_code == 200
        assert detail_a.json()["id"] == sub_id

        # 2. Student B registers and attempts to view Student A's submission -> 403 Forbidden
        headers_b = await _get_auth_headers(
            client, f"stud_b_{uuid.uuid4().hex[:6]}@coderazz.edu", "PasswordB#123", "student"
        )
        unauth_detail = await client.get(f"/api/v1/submissions/{sub_id}", headers=headers_b)
        assert unauth_detail.status_code == 403
        assert "access denied" in unauth_detail.json()["detail"].lower()

        # 3. Admin can view Student A's submission for debugging / grading review
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@coderazz.edu", "password": "AdminInitial#2026"},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        admin_detail = await client.get(f"/api/v1/submissions/{sub_id}", headers=admin_headers)
        assert admin_detail.status_code == 200
        assert admin_detail.json()["id"] == sub_id


# ==============================================================================
# HOSTILE CODE ATTACK SUITE: TESTING DOCKER SANDBOX ISOLATION & RESOURCE LIMITS
# ==============================================================================


@pytest.mark.asyncio
async def test_hostile_infinite_loop_timeout():
    """SECURITY: Verify CPU spinning loop is terminated by watchdog and returns TIME_LIMIT_EXCEEDED."""
    transport = ASGITransport(app=app)
    infinite_loop_code = """
import time
while True:
    pass
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_loop_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": infinite_loop_code,
                "custom_input": "test",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["verdict"] == SubmissionVerdict.TIME_LIMIT_EXCEEDED.value


@pytest.mark.asyncio
async def test_hostile_network_severance():
    """SECURITY: Verify outgoing network requests are blocked by --network none."""
    transport = ASGITransport(app=app)
    network_code = """
import urllib.request
try:
    urllib.request.urlopen("http://1.1.1.1", timeout=2)
    print("NETWORK_SUCCESS")
except Exception as e:
    print(f"NETWORK_BLOCKED: {type(e).__name__}")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_net_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": network_code,
                "custom_input": "test",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "NETWORK_BLOCKED" in data["stdout"]
        assert "NETWORK_SUCCESS" not in data["stdout"]


@pytest.mark.asyncio
async def test_hostile_filesystem_write_blocked():
    """SECURITY: Verify write operations to root filesystem are blocked by --read-only."""
    transport = ASGITransport(app=app)
    fs_write_code = """
try:
    with open("/malicious_payload.sh", "w") as f:
        f.write("echo pwned")
    print("WRITE_SUCCESS")
except OSError as e:
    print(f"WRITE_BLOCKED: {e}")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_fs_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": fs_write_code,
                "custom_input": "test",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "WRITE_BLOCKED" in data["stdout"]
        assert "WRITE_SUCCESS" not in data["stdout"]


@pytest.mark.asyncio
async def test_hostile_memory_exhaustion():
    """SECURITY: Verify excessive RAM allocation is constrained by 128MB container ceiling."""
    transport = ASGITransport(app=app)
    memory_bomb_code = """
# Attempt to allocate 500 MB (container limit is 128 MB)
chunks = []
try:
    for _ in range(50):
        chunks.append(b"A" * (10 * 1024 * 1024))
    print("ALLOC_SUCCESS")
except MemoryError:
    print("MEMORY_CAUGHT")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_mem_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": memory_bomb_code,
                "custom_input": "test",
            },
        )
        assert res.status_code == 200
        data = res.json()
        # Either MemoryError caught inside container or killed by OOM
        assert "ALLOC_SUCCESS" not in data["stdout"]
        assert (
            "MEMORY_CAUGHT" in data["stdout"]
            or data["verdict"] in (
                SubmissionVerdict.MEMORY_LIMIT_EXCEEDED.value,
                SubmissionVerdict.RUNTIME_ERROR.value,
            )
        )


@pytest.mark.asyncio
async def test_hostile_output_flooding_truncated():
    """SECURITY: Verify runaway stdout flooding is capped at 64 KB without memory explosion."""
    transport = ASGITransport(app=app)
    flood_code = """
for _ in range(50000):
    print("FLOOD_LINE_" * 10)
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"stud_flood_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={
                "code": flood_code,
                "custom_input": "test",
            },
        )
        assert res.status_code == 200
        data = res.json()
        # Output must be truncated to <= 65536 bytes (64 KB ceiling)
        assert len(data["stdout"].encode("utf-8")) <= 65536 + 200
        assert "output truncated" in data["stdout"].lower() or len(data["stdout"]) <= 65536


@pytest.mark.asyncio
async def test_docker_cleanup_no_orphans():
    """SECURITY: Verify ephemeral execution containers are killed and pruned with 0 orphans."""
    # Check docker ps for any containers with prefix coderazz-exec
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "ps",
        "--filter",
        "name=coderazz-exec",
        "--format",
        "{{.ID}}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    assert proc.returncode == 0
    active_orphans = [line.strip() for line in stdout.decode("utf-8").splitlines() if line.strip()]
    assert len(active_orphans) == 0, f"Detected orphaned execution containers: {active_orphans}"


@pytest.mark.asyncio
async def test_docker_unavailable_guard():
    """SECURITY: When Docker daemon is unavailable, system returns 503 and NEVER falls back to host."""
    transport = ASGITransport(app=app)
    with patch.object(SandboxService, "is_docker_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = False
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await _get_auth_headers(
                client, f"stud_guard_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
            )
            res = await client.post(
                "/api/v1/submissions/run",
                headers=headers,
                json={"code": "print('hello')", "custom_input": ""},
            )
            assert res.status_code == 503
            assert "offline or unavailable" in res.json()["detail"].lower()
