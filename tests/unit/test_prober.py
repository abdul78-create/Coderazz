"""Unit and integration tests for Diagnostic Micro-Prober (ml/prober.py)."""

import pytest

from backend.app.models.submission import SubmissionVerdict
from backend.app.services.sandbox import SandboxExecutionResult, SandboxService
from ml.prober import DiagnosticProber, MicroProbe


def test_prober_heuristic_empty_input_index_error():
    prober = DiagnosticProber()
    probe = MicroProbe(name="empty_input", description="empty", stdin_input="")
    exec_res = SandboxExecutionResult(
        verdict=SubmissionVerdict.RUNTIME_ERROR,
        exit_code=1,
        stdout="",
        stderr="Traceback:\n  File 'code.py', line 2\n    return arr[0]\nIndexError: list index out of range\n",
        runtime_ms=10,
        memory_kb=1024,
    )
    outcome = prober._evaluate_probe_output(probe, exec_res)
    assert outcome.inferred_misconception == "A3"
    assert outcome.confidence >= 0.90
    assert outcome.exception_name == "IndexError"


def test_prober_heuristic_single_element_index_error():
    prober = DiagnosticProber()
    probe = MicroProbe(name="single_element", description="single", stdin_input="1")
    exec_res = SandboxExecutionResult(
        verdict=SubmissionVerdict.RUNTIME_ERROR,
        exit_code=1,
        stdout="",
        stderr="IndexError: list index out of range",
        runtime_ms=12,
        memory_kb=1024,
    )
    outcome = prober._evaluate_probe_output(probe, exec_res)
    assert outcome.inferred_misconception == "A1"
    assert outcome.confidence >= 0.90


def test_prober_heuristic_recursion_error():
    prober = DiagnosticProber()
    probe = MicroProbe(name="empty_input", description="empty", stdin_input="")
    exec_res = SandboxExecutionResult(
        verdict=SubmissionVerdict.RUNTIME_ERROR,
        exit_code=1,
        stdout="",
        stderr="RecursionError: maximum recursion depth exceeded",
        runtime_ms=45,
        memory_kb=2048,
    )
    outcome = prober._evaluate_probe_output(probe, exec_res)
    assert outcome.inferred_misconception == "D1"
    assert outcome.confidence >= 0.95


def test_prober_heuristic_key_error():
    prober = DiagnosticProber()
    probe = MicroProbe(name="zero_boundary", description="zero", stdin_input="0")
    exec_res = SandboxExecutionResult(
        verdict=SubmissionVerdict.RUNTIME_ERROR,
        exit_code=1,
        stdout="",
        stderr="KeyError: 'target'",
        runtime_ms=15,
        memory_kb=1024,
    )
    outcome = prober._evaluate_probe_output(probe, exec_res)
    assert outcome.inferred_misconception == "E2"
    assert outcome.confidence >= 0.90


@pytest.mark.asyncio
async def test_prober_real_docker_sandbox_execution():
    """Verify that prober executes code inside the real Docker sandbox container."""
    service = SandboxService()
    if not await service.is_docker_available():
        pytest.skip("Docker daemon not available for integration probe")

    prober = DiagnosticProber(sandbox_service=service)
    probe = MicroProbe(name="empty_input", description="empty", stdin_input="\n")
    # Code that crashes on empty input
    buggy_code = """import sys
lines = sys.stdin.read().split()
print(lines[0])
"""
    outcome = await prober.run_probe(buggy_code, probe, timeout_seconds=2.0)
    assert outcome.verdict == SubmissionVerdict.RUNTIME_ERROR
    assert outcome.inferred_misconception == "A3"
    assert outcome.confidence >= 0.90
