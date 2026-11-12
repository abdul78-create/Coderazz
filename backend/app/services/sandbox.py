"""Secure Docker Sandbox Execution Service for CodeRazz.

Executes untrusted student code inside disposable, unprivileged Linux Docker containers.
Enforces non-root execution, network severance, read-only root filesystems, resource quotas,
wall-clock timeouts, output size ceilings, and zero secret mounting.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import uuid
from typing import List, Optional

from backend.app.config import get_settings
from backend.app.models.problem import TestCase
from backend.app.models.submission import SubmissionVerdict
from pydantic import BaseModel

logger = logging.getLogger("coderazz.sandbox")


class SandboxExecutionResult(BaseModel):
    """Raw execution metrics and output from a single test case run."""

    verdict: SubmissionVerdict
    exit_code: int
    stdout: str
    stderr: str
    runtime_ms: int
    memory_kb: int
    truncated: bool = False
    error_message: Optional[str] = None


class TestCaseExecutionResult(BaseModel):
    """Result of running code against a specific test case."""

    test_case_id: Optional[str] = None
    order_index: int
    is_hidden: bool
    passed: bool
    verdict: SubmissionVerdict
    runtime_ms: int
    memory_kb: int
    # Sensitive fields masked for hidden test cases
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    stderr: Optional[str] = None
    explanation: Optional[str] = None


class BatchExecutionSummary(BaseModel):
    """Overall outcome of running code across a suite of test cases."""

    overall_verdict: SubmissionVerdict
    test_cases_passed: int
    total_test_cases: int
    max_runtime_ms: int
    max_memory_kb: int
    test_case_results: List[TestCaseExecutionResult]
    first_failing_test_case: Optional[TestCaseExecutionResult] = None


class SandboxUnavailableException(Exception):
    """Raised when Docker daemon is stopped or unreachable."""

    pass


class SandboxService:
    """Manages ephemeral container lifecycles for untrusted student code execution."""

    IMAGE_NAME = "coderazz-python-runner:latest"

    def __init__(self):
        self.settings = get_settings()

    async def is_docker_available(self) -> bool:
        """Check whether the local Docker daemon is running and responsive."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            return proc.returncode == 0
        except Exception as exc:
            logger.warning("Docker availability check failed: %s", exc)
            return False

    async def execute_code_once(
        self,
        code: str,
        input_data: str = "",
        timeout_seconds: Optional[float] = None,
        memory_mb: Optional[int] = None,
        cpu_limit: Optional[float] = None,
    ) -> SandboxExecutionResult:
        """Execute Python code against a single input string in a hardened disposable container.

        NEVER executes untrusted code on bare host. If Docker is offline, raises an error.
        """
        effective_timeout = timeout_seconds or self.settings.SANDBOX_TIMEOUT_SECONDS
        effective_mem = memory_mb or self.settings.SANDBOX_MEM_LIMIT_MB
        effective_cpu = cpu_limit or self.settings.SANDBOX_CPU_LIMIT

        # 1. Verify Docker availability
        docker_ready = await self.is_docker_available()
        if not docker_ready:
            raise SandboxUnavailableException(
                "Docker execution sandbox is offline or unavailable. "
                "Student code execution is rejected for security. Please start Docker."
            )

        # 2. Create isolated ephemeral host directory for volume mount
        temp_dir = tempfile.mkdtemp(prefix="coderazz_sandbox_")
        container_name = f"coderazz-exec-{uuid.uuid4().hex[:12]}"

        try:
            solution_file = os.path.join(temp_dir, "solution.py")
            input_file = os.path.join(temp_dir, "input.txt")

            with open(solution_file, "w", encoding="utf-8") as f:
                f.write(code)

            with open(input_file, "w", encoding="utf-8") as f:
                f.write(input_data)

            # 3. Assemble hardened Docker CLI arguments
            # Note: Paths on Windows must be normalized for Docker CLI
            host_solution_path = os.path.abspath(solution_file)
            host_input_path = os.path.abspath(input_file)

            cmd = [
                "docker",
                "run",
                "--name",
                container_name,
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=16m",
                "--user",
                "10001:10001",
                "--cap-drop=ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "32",
                "--cpus",
                str(effective_cpu),
                "--memory",
                f"{effective_mem}m",
                "--memory-swap",
                f"{effective_mem}m",
                "--env",
                "PYTHONUNBUFFERED=1",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "-v",
                f"{host_solution_path}:/app/solution.py:ro",
                "-v",
                f"{host_input_path}:/app/input.txt:ro",
                self.IMAGE_NAME,
            ]

            # 4. Launch subprocess
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                # Enforce application-level wall-clock timeout watchdog
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=effective_timeout + 1.0,
                )
            except asyncio.TimeoutError:
                # Forcefully kill container if it exceeds execution time
                logger.warning(
                    "Execution %s exceeded timeout of %ss. Killing container...",
                    container_name,
                    effective_timeout,
                )
                await self._force_kill_container(container_name)
                try:
                    proc.kill()
                    await proc.wait()
                except (ProcessLookupError, OSError):
                    pass
                return SandboxExecutionResult(
                    verdict=SubmissionVerdict.TIME_LIMIT_EXCEEDED,
                    exit_code=124,
                    stdout="",
                    stderr=f"Execution timed out after {effective_timeout} seconds.",
                    runtime_ms=int(effective_timeout * 1000),
                    memory_kb=0,
                    truncated=False,
                    error_message=f"Time Limit Exceeded ({effective_timeout}s)",
                )

            # 5. Parse container harness output
            raw_output = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

            # The harness outputs JSON on the last line of stdout
            if raw_output:
                try:
                    # Look for JSON payload in lines
                    last_line = raw_output.splitlines()[-1]
                    harness_data = json.loads(last_line)
                    exit_code = harness_data.get("exit_code", proc.returncode)
                    stdout = harness_data.get("stdout", "")
                    stderr = harness_data.get("stderr", stderr_text)
                    runtime_ms = harness_data.get("runtime_ms", 0)
                    memory_kb = harness_data.get("memory_kb", 0)
                    truncated = harness_data.get("truncated", False)
                    error_msg = harness_data.get("error")
                except (json.JSONDecodeError, IndexError):
                    exit_code = proc.returncode
                    stdout = raw_output
                    stderr = stderr_text
                    runtime_ms = 0
                    memory_kb = 0
                    truncated = False
                    error_msg = "Failed to parse harness JSON output"
            else:
                exit_code = proc.returncode
                stdout = ""
                stderr = stderr_text
                runtime_ms = 0
                memory_kb = 0
                truncated = False
                error_msg = None

            # 6. Map process exit code to verdict
            verdict = self._determine_verdict(exit_code, stderr, runtime_ms, effective_timeout)

            err_detail = error_msg or (stderr if verdict != SubmissionVerdict.ACCEPTED else None)
            return SandboxExecutionResult(
                verdict=verdict,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                runtime_ms=runtime_ms,
                memory_kb=memory_kb,
                truncated=truncated,
                error_message=err_detail,
            )

        finally:
            # Clean up host temporary files safely
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _force_kill_container(self, container_name: str) -> None:
        """Forcefully kill and remove a container by name."""
        try:
            kill_proc = await asyncio.create_subprocess_exec(
                "docker",
                "kill",
                container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await kill_proc.communicate()
        except Exception as e:
            logger.error("Failed to kill container %s: %s", container_name, e)

    def _determine_verdict(
        self, exit_code: int, stderr: str, runtime_ms: int, timeout_sec: float
    ) -> SubmissionVerdict:
        """Derive standard competitive programming verdict from exit code and diagnostics."""
        # 137 = SIGKILL (often OOM or manual timeout kill)
        if exit_code == 137:
            if runtime_ms >= int(timeout_sec * 1000):
                return SubmissionVerdict.TIME_LIMIT_EXCEEDED
            return SubmissionVerdict.MEMORY_LIMIT_EXCEEDED

        if exit_code == 124:
            return SubmissionVerdict.TIME_LIMIT_EXCEEDED

        if exit_code != 0:
            if "SyntaxError" in stderr or "IndentationError" in stderr:
                return SubmissionVerdict.COMPILATION_ERROR
            return SubmissionVerdict.RUNTIME_ERROR

        return SubmissionVerdict.ACCEPTED

    async def evaluate_test_cases(
        self,
        code: str,
        test_cases: List[TestCase],
        stop_on_first_failure: bool = False,
        timeout_seconds: Optional[float] = None,
    ) -> BatchExecutionSummary:
        """Evaluate code against a list of test cases in sequence."""
        results: List[TestCaseExecutionResult] = []
        overall_verdict = SubmissionVerdict.ACCEPTED
        passed_count = 0
        max_runtime = 0
        max_mem = 0
        first_failure: Optional[TestCaseExecutionResult] = None

        for tc in test_cases:
            run_result = await self.execute_code_once(
                code=code,
                input_data=tc.input_data,
                timeout_seconds=timeout_seconds,
            )

            max_runtime = max(max_runtime, run_result.runtime_ms)
            max_mem = max(max_mem, run_result.memory_kb)

            # Compare output with expected output (trimmed)
            actual_trimmed = run_result.stdout.strip()
            expected_trimmed = tc.expected_output.strip()

            if run_result.verdict != SubmissionVerdict.ACCEPTED:
                # Non-zero exit or timeout
                tc_verdict = run_result.verdict
                is_passed = False
            elif actual_trimmed == expected_trimmed:
                tc_verdict = SubmissionVerdict.ACCEPTED
                is_passed = True
                passed_count += 1
            else:
                tc_verdict = SubmissionVerdict.WRONG_ANSWER
                is_passed = False

            # Create test case result (masking hidden test case inputs/outputs for confidentiality)
            tc_res = TestCaseExecutionResult(
                test_case_id=str(tc.id),
                order_index=tc.order_index,
                is_hidden=tc.is_hidden,
                passed=is_passed,
                verdict=tc_verdict,
                runtime_ms=run_result.runtime_ms,
                memory_kb=run_result.memory_kb,
                input_data=None if tc.is_hidden else tc.input_data,
                expected_output=None if tc.is_hidden else tc.expected_output,
                actual_output=None if tc.is_hidden else actual_trimmed,
                stderr=None if tc.is_hidden else run_result.stderr,
                explanation=tc.explanation if not tc.is_hidden else None,
            )
            results.append(tc_res)

            if not is_passed:
                if overall_verdict == SubmissionVerdict.ACCEPTED:
                    overall_verdict = tc_verdict
                    first_failure = tc_res
                if stop_on_first_failure:
                    break

        return BatchExecutionSummary(
            overall_verdict=overall_verdict,
            test_cases_passed=passed_count,
            total_test_cases=len(test_cases),
            max_runtime_ms=max_runtime,
            max_memory_kb=max_mem,
            test_case_results=results,
            first_failing_test_case=first_failure,
        )


# Global singleton instance
sandbox_service = SandboxService()
