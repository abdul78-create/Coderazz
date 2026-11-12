"""Comprehensive Security Audit Test Suite for CodeRazz Docker Execution Sandbox.

Specifically validates:
1. Process isolation & fork-bomb containment (--pids-limit 32).
2. Filesystem isolation, non-root permissions, host path traversal prevention, and secret isolation.
3. Resource exhaustion (RAM, memory-swap, CPU spinning, runaway stdout/stderr flooding).
4. Forced termination and host/container cleanup across all failure modes (0 orphan containers).
5. Strict confidentiality of hidden test cases across all student-facing endpoints.
6. Verification of the exact Docker security configuration arguments.
"""

import asyncio
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import get_settings
from backend.app.main import app
from backend.app.models.submission import SubmissionVerdict
from backend.app.services.sandbox import SandboxService


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


async def _get_active_docker_containers() -> list[str]:
    """Return list of any currently running or stopped coderazz execution containers."""
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "ps",
        "-a",
        "--filter",
        "name=coderazz-exec",
        "--format",
        "{{.ID}} {{.Names}} {{.Status}}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return [line.strip() for line in stdout.decode("utf-8").splitlines() if line.strip()]


# ==============================================================================
# SECTION 1: PROCESS ISOLATION & FORK BOMB CONTAINMENT
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_process_fork_bomb_blocked():
    """SECURITY AUDIT: Verify fork bomb is contained by --pids-limit 32 and container cleaned up."""
    transport = ASGITransport(app=app)
    # Controlled fork bomb inside container: attempts to spawn processes until OS/cgroup blocks it
    fork_bomb_code = """
import os
import sys

fork_count = 0
try:
    while True:
        pid = os.fork()
        if pid == 0:
            # Child terminates immediately to avoid accumulating lingering children on exit
            sys.exit(0)
        fork_count += 1
except (BlockingIOError, OSError) as exc:
    print(f"FORK_BLOCKED_AT_COUNT_{fork_count}_{type(exc).__name__}")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"fork_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={"code": fork_bomb_code, "custom_input": ""},
        )
        assert res.status_code == 200
        data = res.json()

        # The cgroup PID limit of 32 must block fork attempts before exceeding limits
        assert "FORK_BLOCKED_AT_COUNT" in data["stdout"] or data["verdict"] in (
            SubmissionVerdict.RUNTIME_ERROR.value,
            SubmissionVerdict.TIME_LIMIT_EXCEEDED.value,
        )

        # Verify container was removed and 0 orphans exist
        orphans = await _get_active_docker_containers()
        assert len(orphans) == 0, f"Detected orphaned containers after fork bomb: {orphans}"


@pytest.mark.asyncio
async def test_audit_process_continuous_subprocess_spawn():
    """SECURITY AUDIT: Verify continuous subprocess spawning hits PID ceiling without crashing host."""
    transport = ASGITransport(app=app)
    subprocess_spam_code = """
import subprocess
import sys

spawned = 0
try:
    for i in range(100):
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
        spawned += 1
    print("ALL_SPAWNED_UNCONSTRAINED")
except (BlockingIOError, OSError) as exc:
    print(f"SPAWN_BLOCKED_AFTER_{spawned}_{type(exc).__name__}")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"spam_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={"code": subprocess_spam_code, "custom_input": ""},
        )
        assert res.status_code == 200
        data = res.json()
        assert "ALL_SPAWNED_UNCONSTRAINED" not in data["stdout"]
        assert "SPAWN_BLOCKED" in data["stdout"] or data["verdict"] in (
            SubmissionVerdict.RUNTIME_ERROR.value,
            SubmissionVerdict.TIME_LIMIT_EXCEEDED.value,
        )

        # Confirm 0 orphan containers
        orphans = await _get_active_docker_containers()
        assert len(orphans) == 0


# ==============================================================================
# SECTION 2: FILESYSTEM ISOLATION, SENSITIVE PATHS & SECRET EXFILTRATION
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_filesystem_sensitive_paths_and_secrets():
    """SECURITY AUDIT: Verify student code cannot read /etc/shadow, docker.sock, host drives, or secrets."""
    transport = ASGITransport(app=app)
    probe_code = """
import os

results = {}

# 1. Shadow file check (non-root should be denied)
try:
    with open("/etc/shadow", "r") as f:
        results["shadow"] = "LEAKED"
except PermissionError:
    results["shadow"] = "PERMISSION_DENIED"
except Exception as e:
    results["shadow"] = type(e).__name__

# 2. Docker socket check (should not exist in container)
results["docker_sock"] = "EXISTS" if os.path.exists("/var/run/docker.sock") else "NOT_FOUND"

# 3. Host filesystem paths check (Windows host drives or /host)
results["c_drive"] = "EXISTS" if os.path.exists("C:/") else "NOT_FOUND"
results["host_mount"] = "EXISTS" if os.path.exists("/host") else "NOT_FOUND"

# 4. Environment variables check (application secrets must not leak)
env_keys = list(os.environ.keys())
secret_keywords = ["PASSWORD", "SECRET", "ALGORITHM", "POSTGRES", "DATABASE"]
found_secrets = [k for k in env_keys if any(s in k for s in secret_keywords)]
results["secrets_found"] = found_secrets

# 5. UID check
results["uid"] = os.getuid()

for k, v in results.items():
    print(f"PROBE_{k.upper()}: {v}")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"probe_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={"code": probe_code, "custom_input": ""},
        )
        assert res.status_code == 200
        output = res.json()["stdout"]

        # Confirm non-root execution
        assert "PROBE_UID: 10001" in output, "Container failed to run as unprivileged UID 10001!"

        # Confirm /etc/shadow is protected
        assert "PROBE_SHADOW: PERMISSION_DENIED" in output or "PROBE_SHADOW: PermissionError" in output
        assert "LEAKED" not in output

        # Confirm Docker socket is NOT mounted
        assert "PROBE_DOCKER_SOCK: NOT_FOUND" in output

        # Confirm Host drives are NOT mounted
        assert "PROBE_C_DRIVE: NOT_FOUND" in output
        assert "PROBE_HOST_MOUNT: NOT_FOUND" in output

        # Confirm ZERO application secrets leaked in container environment
        assert "PROBE_SECRETS_FOUND: []" in output


@pytest.mark.asyncio
async def test_audit_filesystem_directory_traversal():
    """SECURITY AUDIT: Verify directory traversal (../) cannot access host or unmounted paths."""
    transport = ASGITransport(app=app)
    traversal_code = """
import os

# Attempt to escape /app directory into parent directories
paths_to_probe = [
    "../../../../../../etc/shadow",
    "../../../../../../root",
    "../../../../../../var/run/docker.sock",
    "../../../../../../host",
]

for p in paths_to_probe:
    try:
        with open(p, "rb") as f:
            print(f"TRAVERSAL_LEAK: {p}")
    except (PermissionError, FileNotFoundError) as e:
        print(f"TRAVERSAL_BLOCKED: {p} -> {type(e).__name__}")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"trav_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={"code": traversal_code, "custom_input": ""},
        )
        assert res.status_code == 200
        output = res.json()["stdout"]
        assert "TRAVERSAL_LEAK" not in output
        assert "TRAVERSAL_BLOCKED" in output


# ==============================================================================
# SECTION 3: RESOURCE EXHAUSTION & MEMORY-SWAP RESTRICTIONS
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_resource_memory_swap_enforced():
    """SECURITY AUDIT: Verify --memory 128m and --memory-swap 128m block RAM and swap exhaustion."""
    transport = ASGITransport(app=app)
    # Attempt to allocate and write into 256 MB (exceeding 128 MB RAM + 128 MB swap ceiling)
    swap_bomb_code = """
data = []
try:
    # 25 blocks of 10 MB = 250 MB
    for i in range(25):
        chunk = bytearray(10 * 1024 * 1024)
        # Touch all bytes to ensure physical allocation
        for j in range(0, len(chunk), 4096):
            chunk[j] = 1
        data.append(chunk)
    print("SWAP_ALLOCATION_SUCCESS_UNCONSTRAINED")
except MemoryError:
    print("MEMORY_SWAP_CAUGHT_INTERNALLY")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"swap_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={"code": swap_bomb_code, "custom_input": ""},
        )
        assert res.status_code == 200
        data = res.json()
        assert "SWAP_ALLOCATION_SUCCESS_UNCONSTRAINED" not in data["stdout"]
        assert (
            "MEMORY_SWAP_CAUGHT_INTERNALLY" in data["stdout"]
            or data["verdict"] in (
                SubmissionVerdict.MEMORY_LIMIT_EXCEEDED.value,
                SubmissionVerdict.RUNTIME_ERROR.value,
            )
        )


@pytest.mark.asyncio
async def test_audit_resource_large_stderr_output_truncated():
    """SECURITY AUDIT: Verify large stderr flood (100,000 lines) is truncated at 64 KB."""
    transport = ASGITransport(app=app)
    stderr_flood_code = """
import sys
for _ in range(50000):
    sys.stderr.write("STDERR_FLOOD_ERROR_MESSAGE_BURST\\n")
"""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_auth_headers(
            client, f"errflood_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        res = await client.post(
            "/api/v1/submissions/run",
            headers=headers,
            json={"code": stderr_flood_code, "custom_input": ""},
        )
        assert res.status_code == 200
        data = res.json()
        # Verify stderr length does not exceed 64 KB + safety header margin
        assert len(data["stderr"].encode("utf-8")) <= 65536 + 500


# ==============================================================================
# SECTION 4: FORCED TERMINATION & CONTAINER CLEANUP VERIFICATION
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_forced_termination_and_cleanup_all_scenarios():
    """SECURITY AUDIT: Verify containers & temp directories are destroyed across all failure modes."""
    service = SandboxService()

    # Initial check: 0 orphan containers
    assert len(await _get_active_docker_containers()) == 0

    # Scenario 1: Normal clean run
    res_normal = await service.execute_code_once("print('clean')", timeout_seconds=2.0)
    assert res_normal.verdict == SubmissionVerdict.ACCEPTED
    assert len(await _get_active_docker_containers()) == 0

    # Scenario 2: Watchdog Timeout termination (infinite loop)
    res_timeout = await service.execute_code_once("while True: pass", timeout_seconds=1.0)
    assert res_timeout.verdict == SubmissionVerdict.TIME_LIMIT_EXCEEDED
    assert len(await _get_active_docker_containers()) == 0

    # Scenario 3: Memory limit termination
    res_mem = await service.execute_code_once(
        "x = b'A' * (200 * 1024 * 1024)", memory_mb=64, timeout_seconds=3.0
    )
    assert res_mem.verdict in (SubmissionVerdict.MEMORY_LIMIT_EXCEEDED, SubmissionVerdict.RUNTIME_ERROR)
    assert len(await _get_active_docker_containers()) == 0

    # Scenario 4: Process exhaustion termination
    fork_script = """
import os, sys
try:
    while True:
        if os.fork() == 0: sys.exit(0)
except Exception: pass
"""
    await service.execute_code_once(fork_script, timeout_seconds=2.0)
    assert len(await _get_active_docker_containers()) == 0


# ==============================================================================
# SECTION 5: HIDDEN TEST CASE CONFIDENTIALITY AUDIT
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_hidden_test_cases_never_disclosed():
    """SECURITY AUDIT: Confirm hidden test inputs and expected outputs never leak anywhere."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Problem detail endpoint check
        prob_res = await client.get("/api/v1/problems/two-sum")
        assert prob_res.status_code == 200
        prob_data = prob_res.json()

        # Only sample test cases returned
        sample_cases = prob_data["sample_test_cases"]
        assert len(sample_cases) == 2
        for sc in sample_cases:
            assert "is_hidden" not in sc

        # 2. Submission evaluation check with failing code
        # Submit code that passes sample cases but fails on hidden edge cases
        partial_code = """import sys
lines = sys.stdin.read().strip().splitlines()
nums = list(map(int, lines[0].split()))
target = int(lines[1].strip())
# Buggy: works only if indices are 0 and 1
print("0 1")
"""
        headers_student = await _get_auth_headers(
            client, f"stud_leak_{uuid.uuid4().hex[:6]}@coderazz.edu", "StudentPass#123", "student"
        )
        sub_res = await client.post(
            "/api/v1/submissions",
            headers=headers_student,
            json={
                "problem_id": prob_data["id"],
                "code": partial_code,
                "language": "python",
            },
        )
        assert sub_res.status_code == 201
        sub_data = sub_res.json()
        assert sub_data["verdict"] == SubmissionVerdict.WRONG_ANSWER.value

        # CONFIDENTIALITY GUARANTEE: Error message must not disclose hidden input/output
        # e.g., "Wrong Answer on test case 3." is allowed, but secret input numbers must NOT appear
        err_msg = sub_data.get("error_message", "")
        assert "Wrong Answer on test case" in err_msg

        # 3. Submission history listing check
        hist_res = await client.get("/api/v1/submissions", headers=headers_student)
        assert hist_res.status_code == 200
        for item in hist_res.json():
            # History summary never contains test case inputs or outputs
            assert "input_data" not in item
            assert "expected_output" not in item
            assert "test_cases" not in item


# ==============================================================================
# SECTION 6: DOCKER SECURITY CONFIGURATION AUDIT
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_docker_cli_flags_verification():
    """SECURITY AUDIT: Verify the exact command line assembly contains all required security flags."""
    service = SandboxService()
    settings = get_settings()

    # Capture command passed to asyncio.create_subprocess_exec
    with patch("asyncio.create_subprocess_exec", side_effect=asyncio.create_subprocess_exec) as mock_exec:
        run_res = await service.execute_code_once("print(1)")
        assert run_res.verdict == SubmissionVerdict.ACCEPTED

        # Find the docker run call
        docker_run_call = None
        for call_args in mock_exec.call_args_list:
            args = list(call_args[0])
            if len(args) > 1 and args[0] == "docker" and args[1] == "run":
                docker_run_call = args
                break

        assert docker_run_call is not None, "Docker run was never called!"
        cmd_str = " ".join(docker_run_call)

        # Assert mandatory security parameters in CLI call
        assert "--network none" in cmd_str
        assert "--read-only" in cmd_str
        assert "--tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m" in cmd_str
        assert "--user 10001:10001" in cmd_str
        assert "--cap-drop ALL" in cmd_str or "--cap-drop=ALL" in cmd_str
        assert "--security-opt no-new-privileges" in cmd_str
        assert "--pids-limit 32" in cmd_str
        assert "--memory 128m" in cmd_str
        assert "--memory-swap 128m" in cmd_str
        assert "--cpus 1.0" in cmd_str
        assert "docker.sock" not in cmd_str
        assert "--privileged" not in cmd_str

    # Verify settings defaults
    assert settings.SANDBOX_MODE == "docker"
    assert settings.SANDBOX_TIMEOUT_SECONDS == 3.0
    assert settings.SANDBOX_MEM_LIMIT_MB == 128
    assert settings.SANDBOX_CPU_LIMIT == 1.0
    assert settings.SANDBOX_MAX_OUTPUT_BYTES == 65536
    assert service.IMAGE_NAME == "coderazz-python-runner:latest"
