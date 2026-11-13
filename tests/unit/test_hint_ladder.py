"""Unit tests for the 5-Tier Progressive Hint Generator."""

from unittest.mock import MagicMock

import pytest

from backend.app.services.hint_ladder import (
    TIER_NAMES,
    TIER_PENALTIES,
    GeneratedHint,
    HintLadderService,
)
from ml.leak_guard import LeakGuardResult, SolutionLeakGuard

TWO_SUM_SOLUTION = """import sys
def solve():
    lines = sys.stdin.read().strip().splitlines()
    nums = list(map(int, lines[0].split()))
    target = int(lines[1].strip())
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            print(f"{seen[diff]} {i}")
            return
        seen[n] = i
solve()
"""


@pytest.fixture
def hint_service() -> HintLadderService:
    """HintLadderService fixture."""
    return HintLadderService()


def test_hint_generation_all_5_tiers(hint_service: HintLadderService) -> None:
    """Verify progressive hint generation from Level 1 to Level 5 for A1."""
    student_code = "def loop(arr):\n    for i in range(len(arr) + 1):\n        print(arr[i])"

    for level in range(1, 6):
        hint: GeneratedHint = hint_service.generate_hint(
            hint_level=level,
            misconception_code="A1",
            reference_solution=TWO_SUM_SOLUTION,
            problem_title="Two Sum",
            evidence_lines=[2],
            student_code=student_code,
            taxonomy_remedy="Check range boundaries; range(n) stops at n-1.",
            taxonomy_name="Off-by-one in loop bounds",
        )

        assert hint.hint_level == level
        assert hint.hint_tier_name == TIER_NAMES[level]
        assert hint.penalty_score == TIER_PENALTIES[level]
        assert hint.leak_check_passed is True
        assert hint.fallback_used is False
        assert len(hint.hint_content) > 20

        # Level 5 targeted pointer should reference the faulty code line
        if level == 5:
            assert "Line 2" in hint.hint_content
            assert "for i in range(len(arr) + 1):" in hint.hint_content


def test_d4_accumulator_return_analogue_passes_leak_guard(hint_service: HintLadderService) -> None:
    """Verify D4 worked analogue (Level 4) contains safe code that passes leak guard."""
    hint: GeneratedHint = hint_service.generate_hint(
        hint_level=4,
        misconception_code="D4",
        reference_solution=TWO_SUM_SOLUTION,
        taxonomy_name="Return inside accumulator loop",
    )

    assert hint.hint_level == 4
    assert hint.leak_check_passed is True
    assert hint.fallback_used is False
    assert "calculate_total_weight" in hint.hint_content
    assert "OUTSIDE the loop" in hint.hint_content


def test_leak_guard_triggers_safe_fallback() -> None:
    """If SolutionLeakGuard detects a leak, the service must fallback to safe conceptual remedy."""
    mock_leak_guard = MagicMock(spec=SolutionLeakGuard)
    # Simulate a detected leak
    mock_leak_guard.check_leak.return_value = LeakGuardResult(
        is_leaked=True,
        severity_score=0.95,
        leak_reasons=["Direct code copy-paste detected"],
    )

    service = HintLadderService(leak_guard=mock_leak_guard)
    hint: GeneratedHint = service.generate_hint(
        hint_level=5,
        misconception_code="A1",
        reference_solution=TWO_SUM_SOLUTION,
        taxonomy_name="Off-by-one in loop bounds",
        taxonomy_remedy="Remember that range(stop) stops at stop - 1.",
    )

    assert hint.leak_check_passed is False
    assert hint.fallback_used is True
    assert hint.leak_severity == 0.95
    assert "Pedagogical Guidance: Off-by-one in loop bounds" in hint.hint_title
    assert "Direct code suggestions have been restricted" in hint.hint_content
    assert "Remember that range(stop) stops at stop - 1." in hint.hint_content


def test_generic_fallback_for_unmodeled_misconceptions(hint_service: HintLadderService) -> None:
    """Unmodeled taxonomy codes fallback to generic structured tier templates."""
    hint: GeneratedHint = hint_service.generate_hint(
        hint_level=2,
        misconception_code="F3",
        reference_solution=TWO_SUM_SOLUTION,
        taxonomy_name="Unnecessary duplicate sort",
        taxonomy_remedy="Avoid sorting a list that is already ordered.",
    )

    assert hint.hint_level == 2
    assert hint.hint_tier_name == TIER_NAMES[2]
    assert "Unnecessary duplicate sort" in hint.hint_title
    assert "Avoid sorting a list that is already ordered." in hint.hint_content
    assert hint.leak_check_passed is True


def test_invalid_hint_level_raises_error(hint_service: HintLadderService) -> None:
    """Hint levels below 1 or above 5 must raise ValueError."""
    with pytest.raises(ValueError, match="between 1 and 5"):
        hint_service.generate_hint(
            hint_level=0,
            misconception_code="A1",
            reference_solution=TWO_SUM_SOLUTION,
        )

    with pytest.raises(ValueError, match="between 1 and 5"):
        hint_service.generate_hint(
            hint_level=6,
            misconception_code="A1",
            reference_solution=TWO_SUM_SOLUTION,
        )

