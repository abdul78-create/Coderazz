"""Diagnostic Micro-Prober for CodeRazz Misconception Engine.

Generates targeted micro-test boundary inputs (e.g., empty arrays, single elements,
duplicates, negative values) to isolate ambiguous failures and distinguish between
competing misconception hypotheses.

Integrates with SandboxService to run probes inside isolated Docker containers
respecting --pids-limit 32, 128 MB RAM limit, and watchdog timeouts.
"""

import logging
from dataclasses import dataclass, field

from backend.app.models.submission import SubmissionVerdict
from backend.app.services.sandbox import SandboxExecutionResult, SandboxService

logger = logging.getLogger(__name__)


@dataclass
class MicroProbe:
    """Definition of a diagnostic boundary probe."""

    name: str
    description: str
    stdin_input: str
    targeted_misconceptions: list[str] = field(default_factory=list)


@dataclass
class ProbeOutcome:
    """Observed result from executing a single probe in the sandbox."""

    probe_name: str
    stdin_input: str
    verdict: SubmissionVerdict
    stdout: str = ""
    stderr: str = ""
    exception_name: str | None = None
    runtime_ms: int = 0
    inferred_misconception: str | None = None
    confidence: float = 0.0
    evidence_explanation: str = ""


# Standard library of introductory programming boundary probes
STANDARD_PROBES = [
    MicroProbe(
        name="empty_input",
        description="Empty list or zero input to test base boundary handling",
        stdin_input="\n",
        targeted_misconceptions=["A3", "C1", "D1"],
    ),
    MicroProbe(
        name="single_element",
        description="Single element collection to detect premature indexing assumptions",
        stdin_input="42\n",
        targeted_misconceptions=["A1", "A3", "D4"],
    ),
    MicroProbe(
        name="duplicate_elements",
        description="Duplicate values to detect hashing/dictionary key collisions or inner loop shadowing",
        stdin_input="2 2\n4\n",
        targeted_misconceptions=["A4", "E2", "F2"],
    ),
    MicroProbe(
        name="zero_boundary",
        description="Input containing 0 to catch falsy zero evaluation bugs",
        stdin_input="0\n",
        targeted_misconceptions=["B2", "C4"],
    ),
    MicroProbe(
        name="negative_value",
        description="Negative number input to test sign logic and comparison predicates",
        stdin_input="-5\n",
        targeted_misconceptions=["B2", "B5"],
    ),
]


class DiagnosticProber:
    """Generates and executes micro-probes against student code inside the sandbox."""

    def __init__(self, sandbox_service: SandboxService | None = None) -> None:
        self.sandbox = sandbox_service or SandboxService()

    async def run_probe(
        self,
        code: str,
        probe: MicroProbe,
        timeout_seconds: float = 1.5,
    ) -> ProbeOutcome:
        """Execute a single diagnostic probe inside an isolated Docker container.

        Enforces --pids-limit 32, 128 MB RAM ceiling, and watchdog timeout.
        """
        try:
            exec_res: SandboxExecutionResult = await self.sandbox.execute_code_once(
                code=code,
                input_data=probe.stdin_input,
                timeout_seconds=timeout_seconds,
                memory_mb=128,
            )
        except (OSError, RuntimeError, TimeoutError) as err:
            logger.warning("Sandbox failure during probe execution '%s': %s", probe.name, err)
            return ProbeOutcome(
                probe_name=probe.name,
                stdin_input=probe.stdin_input,
                verdict=SubmissionVerdict.SANDBOX_ERROR,
                evidence_explanation=f"Probe failed to execute in sandbox: {err}",
            )

        # Analyze runtime output & exception signatures
        outcome = self._evaluate_probe_output(probe, exec_res)
        return outcome

    async def run_diagnostic_suite(
        self,
        code: str,
        probes: list[MicroProbe] | None = None,
        max_probes: int = 3,
    ) -> list[ProbeOutcome]:
        """Run a suite of targeted micro-probes, stopping early if a definitive signature fires."""
        if probes is None:
            probes = STANDARD_PROBES[:max_probes]

        outcomes: list[ProbeOutcome] = []
        for probe in probes:
            outcome = await self.run_probe(code, probe)
            outcomes.append(outcome)

            # If high-confidence signature detected, return immediately to conserve runner cycles
            if outcome.confidence >= 0.90:
                break

        return outcomes

    def _evaluate_probe_output(
        self,
        probe: MicroProbe,
        res: SandboxExecutionResult,
    ) -> ProbeOutcome:
        """Infer misconception from stderr trace or execution verdict on probe."""
        exception_name = None
        stderr = res.stderr or ""
        stdout = res.stdout or ""

        # Extract standard Python exception name from traceback
        for line in reversed(stderr.splitlines()):
            stripped = line.strip()
            if ": " in stripped:
                left_side = stripped.split(":", 1)[0].strip()
                if left_side.endswith("Error") or left_side in ("Exception", "SyntaxError"):
                    exception_name = left_side
                    break
            for err_type in [
                "IndexError", "KeyError", "TypeError", "ZeroDivisionError",
                "RecursionError", "UnboundLocalError", "NameError", "SyntaxError",
            ]:
                if err_type in line:
                    exception_name = err_type
                    break
            if exception_name:
                break

        inferred = None
        confidence = 0.0
        explanation = ""

        # Pattern 1: IndexError on empty or single element
        if exception_name == "IndexError":
            if probe.name == "empty_input":
                inferred = "A3"
                confidence = 0.92
                explanation = "Code crashed with IndexError when tested with empty input (accessing element in empty collection)."
            elif probe.name == "single_element":
                inferred = "A1"
                confidence = 0.90
                explanation = "Code crashed with IndexError when tested with a single-element list (assuming array length >= 2)."

        # Pattern 2: RecursionError on empty or zero
        elif exception_name == "RecursionError":
            inferred = "D1"
            confidence = 0.95
            explanation = "Code exceeded maximum recursion depth, indicating a missing or non-converging recursive base case."

        # Pattern 3: UnboundLocalError / NameError
        elif exception_name in ("UnboundLocalError", "NameError"):
            inferred = "C1"
            confidence = 0.96
            explanation = f"Code raised {exception_name}, indicating usage of an uninitialized or unassigned variable."

        # Pattern 4: KeyError
        elif exception_name == "KeyError":
            inferred = "E2"
            confidence = 0.93
            explanation = "Code raised KeyError, attempting to look up a key in a dictionary without checking membership."

        # Pattern 5: Time Limit Exceeded
        elif res.verdict == SubmissionVerdict.TIME_LIMIT_EXCEEDED:
            inferred = "A2"
            confidence = 0.88
            explanation = f"Execution timed out on probe '{probe.name}', demonstrating an infinite loop condition."

        return ProbeOutcome(
            probe_name=probe.name,
            stdin_input=probe.stdin_input,
            verdict=res.verdict,
            stdout=stdout,
            stderr=stderr,
            exception_name=exception_name,
            runtime_ms=res.runtime_ms,
            inferred_misconception=inferred,
            confidence=confidence,
            evidence_explanation=explanation,
        )
