"""Unit tests for the SolutionLeakGuard firewall in ml/leak_guard.py."""

import pytest

from ml.leak_guard import LeakGuardResult, SolutionLeakGuard

# Reference solution for Two-Sum
TWO_SUM_REFERENCE = """import sys

def solve():
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        return
    nums = list(map(int, lines[0].split()))
    target = int(lines[1].strip())
    
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            print(f"{seen[diff]} {i}")
            return
        seen[n] = i

if __name__ == '__main__':
    solve()
"""

# Reference solution for Reverse-String
REVERSE_STRING_REFERENCE = """import sys

def solve():
    s = sys.stdin.read().strip()
    res = []
    for i in range(len(s) - 1, -1, -1):
        res.append(s[i])
    print("".join(res))

if __name__ == '__main__':
    solve()
"""


@pytest.fixture
def guard() -> SolutionLeakGuard:
    """SolutionLeakGuard instance fixture."""
    return SolutionLeakGuard()


def test_direct_code_copy_paste_blocked(guard: SolutionLeakGuard) -> None:
    """Direct copy-pasting of reference solution lines must be strictly blocked."""
    leaking_hint = (
        "Here is what you need to write in your loop:\n"
        "```python\n"
        "for i, n in enumerate(nums):\n"
        "    diff = target - n\n"
        "    if diff in seen:\n"
        "        print(f'{seen[diff]} {i}')\n"
        "        return\n"
        "```"
    )
    res: LeakGuardResult = guard.check_leak(leaking_hint, TWO_SUM_REFERENCE)

    assert res.is_leaked is True
    assert res.severity_score >= 0.90
    assert any("Direct code copy-paste" in reason or "Structural AST leak" in reason for reason in res.leak_reasons)
    assert len(res.matched_snippets) > 0


def test_variable_renaming_bypass_blocked(guard: SolutionLeakGuard) -> None:
    """Renaming variable identifiers (e.g. seen->lookup, nums->arr, diff->rem) must be detected."""
    renamed_hint = (
        "Try using this hash map approach:\n"
        "```python\n"
        "lookup = {}\n"
        "for idx, val in enumerate(arr):\n"
        "    rem = goal - val\n"
        "    if rem in lookup:\n"
        "        print(f'{lookup[rem]} {idx}')\n"
        "        return\n"
        "    lookup[val] = idx\n"
        "```"
    )
    res: LeakGuardResult = guard.check_leak(renamed_hint, TWO_SUM_REFERENCE)

    assert res.is_leaked is True
    assert res.severity_score >= 0.85
    assert any(
        "Structural AST leak" in reason or "Token sequence leak" in reason or "overlap" in reason
        for reason in res.leak_reasons
    )


def test_structural_ast_leak_blocked(guard: SolutionLeakGuard) -> None:
    """Isomorphic loop structure or core condition subtree must be blocked."""
    structural_hint = (
        "Look at this loop logic:\n"
        "```python\n"
        "diff = target - n\n"
        "if diff in seen:\n"
        "    return seen[diff], i\n"
        "```"
    )
    res: LeakGuardResult = guard.check_leak(structural_hint, TWO_SUM_REFERENCE)

    assert res.is_leaked is True
    assert res.severity_score >= 0.65


def test_reverse_string_renamed_loop_blocked(guard: SolutionLeakGuard) -> None:
    """Reverse string backwards index loop must be caught even if variable renamed."""
    leaking_hint = (
        "Here is the loop for reversing:\n"
        "```python\n"
        "for k in range(len(text) - 1, -1, -1):\n"
        "    chars.append(text[k])\n"
        "```"
    )
    res: LeakGuardResult = guard.check_leak(leaking_hint, REVERSE_STRING_REFERENCE)

    assert res.is_leaked is True
    assert res.severity_score >= 0.70


def test_safe_conceptual_hint_permitted(guard: SolutionLeakGuard) -> None:
    """High-level conceptual guidance without solution code must be permitted."""
    safe_hint = (
        "When iterating through numbers, you can store previously seen elements "
        "in a dictionary to check if their complement has already been processed "
        "in O(1) average time."
    )
    res: LeakGuardResult = guard.check_leak(safe_hint, TWO_SUM_REFERENCE)

    assert res.is_leaked is False
    assert res.severity_score < 0.50
    assert len(res.leak_reasons) == 0


def test_safe_counter_example_hint_permitted(guard: SolutionLeakGuard) -> None:
    """Counter-example test cases with minimal inputs must be permitted."""
    safe_hint = (
        "Consider what happens with the input: nums = [3, 3], target = 6. "
        "Does your solution return [0, 1] or does it get stuck?"
    )
    res: LeakGuardResult = guard.check_leak(safe_hint, TWO_SUM_REFERENCE)

    assert res.is_leaked is False
    assert res.severity_score < 0.50


def test_safe_worked_analogue_permitted(guard: SolutionLeakGuard) -> None:
    """An isomorphic worked analogue solving an unrelated problem must be permitted."""
    analogue_hint = (
        "Here is an example of using a dictionary to count frequencies of words:\n"
        "```python\n"
        "frequencies = {}\n"
        "for word in word_list:\n"
        "    frequencies[word] = frequencies.get(word, 0) + 1\n"
        "```\n"
        "Notice how each word is stored for instant lookup."
    )
    res: LeakGuardResult = guard.check_leak(analogue_hint, TWO_SUM_REFERENCE)

    assert res.is_leaked is False
    assert res.severity_score < 0.50


def test_empty_inputs_handling(guard: SolutionLeakGuard) -> None:
    """Empty or None hints and solutions return safe results."""
    res1 = guard.check_leak("", TWO_SUM_REFERENCE)
    assert res1.is_leaked is False
    assert res1.severity_score == 0.0

    res2 = guard.check_leak("Some hint", "")
    assert res2.is_leaked is False
    assert res2.severity_score == 0.0
