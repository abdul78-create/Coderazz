"""Progressive 5-Tier Pedagogical Hint Ladder for CodeRazz.

Generates structured, calibrated hints without spoiling answers:
- Level 1: Nudge (Directional Socratic question)
- Level 2: Conceptual Explanation (Clarifies underlying computing principle)
- Level 3: Counter-Example (Minimal tangible input triggering the flaw)
- Level 4: Worked Analogue (Isomorphic pattern on an unrelated problem)
- Level 5: Targeted Pointer (Identifies specific faulty construct)

Every hint is strictly validated through SolutionLeakGuard before delivery.
"""

import logging
from dataclasses import dataclass

from ml.leak_guard import SolutionLeakGuard

logger = logging.getLogger(__name__)

# Penalties associated with progressive hint levels
TIER_PENALTIES = {
    1: 0.00,
    2: 0.05,
    3: 0.10,
    4: 0.15,
    5: 0.25,
}

TIER_NAMES = {
    1: "Level 1: Nudge",
    2: "Level 2: Conceptual Explanation",
    3: "Level 3: Counter-Example",
    4: "Level 4: Worked Analogue",
    5: "Level 5: Targeted Pointer",
}


@dataclass
class GeneratedHint:
    """Delivered pedagogical hint payload."""

    hint_level: int
    hint_tier_name: str
    hint_title: str
    hint_content: str
    penalty_score: float
    leak_check_passed: bool
    leak_severity: float
    fallback_used: bool


# Canonical templates for introductory Python misconceptions
HINT_TEMPLATES: dict[str, dict[int, dict[str, str]]] = {
    # A1: Off-by-one in loop bounds
    "A1": {
        1: {
            "title": "Examine Your Loop Boundaries",
            "content": (
                "Take a close look at how your loop ranges are defined.\n\n"
                "In a 0-indexed language like Python, if a list has length `N`, "
                "what is the exact index of the final element?"
            ),
        },
        2: {
            "title": "Understanding Python 0-Based Indexing & range()",
            "content": (
                "In Python, indexing begins at `0`. A sequence of length `N` contains valid "
                "indices from `0` through `N - 1`.\n\n"
                "The `range(start, stop)` function generates integers up to, but not including, "
                "`stop`.\n\n"
                "Using `range(len(arr) + 1)` generates indices from `0` to `len(arr)`. "
                "Accessing `arr[len(arr)]` raises `IndexError: list index out of range` "
                "because the list ends at `len(arr) - 1`."
            ),
        },
        3: {
            "title": "Minimal Counter-Example",
            "content": (
                "Consider a single-element list:\n"
                "```\n"
                "nums = [42]\n"
                "```\n"
                "Here, `len(nums)` is `1`. The only valid index is `nums[0]`.\n\n"
                "What values does your loop produce, and what index does it attempt to access?"
            ),
        },
        4: {
            "title": "Worked Analogue: Safe Index Iteration",
            "content": (
                "Here is an example demonstrating safe index traversal on an unrelated string:\n\n"
                "```python\n"
                "greeting = 'HELLO'\n\n"
                "# Correct: range(len(greeting)) yields indices 0, 1, 2, 3, 4\n"
                "for idx in range(len(greeting)):\n"
                "    char = greeting[idx]\n"
                "    print(f'Index {idx}: {char}')\n"
                "```\n\n"
                "Notice: passing `len(greeting)` without offset stops before reaching `len(s)`."
            ),
        },
        5: {
            "title": "Targeted Pointer: Adjust Loop Upper Bound",
            "content": (
                "Inspect the loop boundary in your code:\n\n"
                "{evidence_callout}\n\n"
                "Remove any `+ 1` added to the `range(len(...))` upper limit. "
                "If indexing ahead with `arr[i + 1]`, stop the loop at `len(arr) - 1` instead."
            ),
        },
    },

    # A2: Infinite loop condition
    "A2": {
        1: {
            "title": "Check Loop Progression",
            "content": (
                "Is your `while` loop condition guaranteed to change on every iteration?\n\n"
                "Verify whether the variables in your condition are being updated inside the body."
            ),
        },
        2: {
            "title": "While Loop Invariants & Termination",
            "content": (
                "A `while <condition>:` loop continues running as long as the "
                "condition is `True`.\n\n"
                "For the loop to terminate, at least one variable involved in the condition must "
                "be modified inside the loop body toward making the condition `False`."
            ),
        },
        3: {
            "title": "Trace Loop Execution",
            "content": (
                "Step through your loop manually with a small test input.\n\n"
                "Write down the values of your loop variables before the loop, after iteration 1, "
                "and after iteration 2. Are they approaching the exit threshold?"
            ),
        },
        4: {
            "title": "Worked Analogue: Guaranteed While Loop Termination",
            "content": (
                "Here is an analogue showing a countdown while-loop that terminates safely:\n\n"
                "```python\n"
                "countdown = 5\n"
                "while countdown > 0:\n"
                "    print(countdown)\n"
                "    countdown -= 1  # Crucial: decrements toward 0 on every step\n"
                "```"
            ),
        },
        5: {
            "title": "Targeted Pointer: Mutate Condition Variables",
            "content": (
                "{evidence_callout}\n\n"
                "Ensure that your loop counter is updated inside the loop body, "
                "or that a `break` condition is reached."
            ),
        },
    },

    # A3: Index out of range
    "A3": {
        1: {
            "title": "Verify Collection Size Before Indexing",
            "content": (
                "Your code attempted to access an element past the end of a list or string.\n\n"
                "Could the collection be empty, or is an index advancing faster than the size?"
            ),
        },
        2: {
            "title": "Boundary Checking & Empty Collections",
            "content": (
                "In Python, indexing into an empty list `[]` with any index immediately raises "
                "`IndexError`.\n\n"
                "Always verify whether the collection has sufficient elements before "
                "directly subscripting with `[i]`."
            ),
        },
        3: {
            "title": "Minimal Counter-Example",
            "content": (
                "Test your function with an empty list or string `[]` / `''`.\n\n"
                "Does your code check `if not arr:` before accessing elements, or does it "
                "assume at least one item exists?"
            ),
        },
        4: {
            "title": "Worked Analogue: Guarding Direct Subscript Access",
            "content": (
                "Here is an analogue demonstrating safe boundary checking before indexing:\n\n"
                "```python\n"
                "def get_first_and_last(items):\n"
                "    if not items:\n"
                "        return None  # Guard clause handles empty input safely\n"
                "    return items[0], items[-1]\n"
                "```"
            ),
        },
        5: {
            "title": "Targeted Pointer: Add Pre-Access Bound Check",
            "content": (
                "{evidence_callout}\n\n"
                "Add a guard clause at the start of your function to handle empty or undersized "
                "inputs, or ensure your index does not exceed `len(...) - 1`."
            ),
        },
    },

    # A5: Premature loop termination
    "A5": {
        1: {
            "title": "Where Does Your Loop Terminate?",
            "content": (
                "Does your loop run for every element in the collection, or does it stop after "
                "the very first item?"
            ),
        },
        2: {
            "title": "Search Loops & Exit Placement",
            "content": (
                "In a search algorithm, encountering an element that doesn't match the target is "
                "not enough to conclude that the target is absent. You must inspect **all** "
                "elements before deciding the target is missing.\n\n"
                "Placing an unconditional `return False` or `break` inside an `else` branch "
                "within the loop terminates the search prematurely."
            ),
        },
        3: {
            "title": "Counter-Example: Target at the End",
            "content": (
                "Consider searching for `target = 3` in `nums = [1, 2, 3]`.\n\n"
                "On the first iteration (`n = 1`), `n != target`. If your loop immediately "
                "returns `False`, it will never inspect `2` or `3`."
            ),
        },
        4: {
            "title": "Worked Analogue: Proper Linear Search Pattern",
            "content": (
                "Here is the standard pattern for searching an item in a list:\n\n"
                "```python\n"
                "def contains_even_number(numbers):\n"
                "    for num in numbers:\n"
                "        if num % 2 == 0:\n"
                "            return True  # Found match! Exit early\n"
                "    # Loop finished checking ALL elements without finding an even number:\n"
                "    return False\n"
                "```"
            ),
        },
        5: {
            "title": "Targeted Pointer: Move Negative Return Outside Loop",
            "content": (
                "{evidence_callout}\n\n"
                "Move the fallback return statement outside the loop so that it only executes "
                "after all elements have been examined."
            ),
        },
    },

    # D2: Missing explicit return
    "D2": {
        1: {
            "title": "What Does Your Function Return?",
            "content": (
                "Does your function explicitly return a computed value, or does it complete "
                "without a `return` statement?"
            ),
        },
        2: {
            "title": "Implicit None in Python Functions",
            "content": (
                "In Python, any function reaching the end of its body without an explicit `return` "
                "automatically returns `None`.\n\n"
                "Autograders inspect the returned object. If your function computes a result into "
                "a variable but never returns it, the test evaluates your result as `None`."
            ),
        },
        3: {
            "title": "Counter-Example: Inspect Return Value",
            "content": (
                "Call your function in the console: `result = solve(...)` and then "
                "`print(type(result))`.\n\n"
                "If it prints `<class 'NoneType'>`, your calculation is being lost."
            ),
        },
        4: {
            "title": "Worked Analogue: Explicit Return",
            "content": (
                "```python\n"
                "def calculate_perimeter(length, width):\n"
                "    total = 2 * (length + width)\n"
                "    return total  # Explicitly return the calculated value\n"
                "```"
            ),
        },
        5: {
            "title": "Targeted Pointer: Add Final Return Statement",
            "content": (
                "{evidence_callout}\n\n"
                "Add an explicit `return <result>` statement at the end of your function."
            ),
        },
    },

    # D4: Return inside accumulator loop
    "D4": {
        1: {
            "title": "Indentation of Your Return Statement",
            "content": (
                "Check the indentation level of your `return` statement relative to your loop.\n\n"
                "Does it return on the first pass, or after the loop finishes accumulating?"
            ),
        },
        2: {
            "title": "Accumulation Invariant",
            "content": (
                "An accumulator aggregates information across every element in a sequence. "
                "A `return` statement immediately halts function execution.\n\n"
                "If `return` is placed inside the loop body, the function exits during "
                "iteration 1, leaving all remaining items unexamined."
            ),
        },
        3: {
            "title": "Counter-Example: Multi-Element List",
            "content": (
                "Test with a list of multiple items: `[10, 20, 30]`.\n\n"
                "If the expected answer requires processing all 3 items, but your code "
                "returns after adding `10`, the loop was interrupted on its first step."
            ),
        },
        4: {
            "title": "Worked Analogue: Correct Accumulator Placement",
            "content": (
                "Here is an analogue showing proper accumulator return indentation:\n\n"
                "```python\n"
                "def calculate_total_weight(weights):\n"
                "    total = 0\n"
                "    for w in weights:\n"
                "        total += w\n"
                "    # OUTSIDE the loop: return after accumulation completes\n"
                "    return total\n"
                "```"
            ),
        },
        5: {
            "title": "Targeted Pointer: Dedent Return Statement",
            "content": (
                "{evidence_callout}\n\n"
                "Dedent your `return` statement so that it aligns outside the loop header."
            ),
        },
    },

    # G1: Confusing print() with return
    "G1": {
        1: {
            "title": "Print vs. Return",
            "content": (
                "Are you outputting your result with `print()` or returning it with `return`?\n\n"
                "Autograders inspect the return value of functions."
            ),
        },
        2: {
            "title": "Standard Output vs. Function Return Value",
            "content": (
                "`print()` writes text to the standard output stream (the terminal), but does "
                "not produce a value for the caller. Its own return value is always `None`.\n\n"
                "`return` passes the computed object back to the test runner so it can verify "
                "correctness."
            ),
        },
        3: {
            "title": "Trace Function Output",
            "content": (
                "Notice: `val = print(5)` results in `val is None`.\n\n"
                "If an autograder checks `assert solve(...) == expected`, `print()` causes "
                "the test to see `None`."
            ),
        },
        4: {
            "title": "Worked Analogue: Returning Rather Than Printing",
            "content": (
                "```python\n"
                "# Incorrect:\n"
                "def add_bad(a, b):\n"
                "    print(a + b)\n\n"
                "# Correct:\n"
                "def add_good(a, b):\n"
                "    return a + b\n"
                "```"
            ),
        },
        5: {
            "title": "Targeted Pointer: Replace print() with return",
            "content": (
                "{evidence_callout}\n\n"
                "Change `print(...)` to `return ...`."
            ),
        },
    },

    # S1: Syntax Error
    "S1": {
        1: {
            "title": "Syntax Inspection",
            "content": (
                "Python encountered a syntax error before execution. Check for unclosed "
                "parentheses or missing colons."
            ),
        },
        2: {
            "title": "Python Syntax Invariants",
            "content": (
                "Every opening delimiter (`(`, `[`, `{`, `\"`, `'`) must have a matching "
                "closing symbol.\n\n"
                "Compound statements (`def`, `for`, `while`, `if`, `else`) must end with `:`."
            ),
        },
        3: {
            "title": "Line-by-Line Delimiter Balance",
            "content": (
                "Check the line indicated in the traceback and the line immediately preceding "
                "it for unclosed parentheses."
            ),
        },
        4: {
            "title": "Syntax Checklist",
            "content": (
                "1. Colons `:` at the end of headers\n"
                "2. Matching parentheses `()`\n"
                "3. Matching quotes `\"` or `'`\n"
                "4. Consistent 4-space indentation"
            ),
        },
        5: {
            "title": "Targeted Pointer: Fix Delimiter on Faulty Line",
            "content": (
                "{evidence_callout}\n\n"
                "Resolve the syntax discrepancy indicated on this line."
            ),
        },
    },
}


class HintLadderService:
    """Service generating calibrated, leak-protected progressive hints."""

    def __init__(self, leak_guard: SolutionLeakGuard | None = None) -> None:
        self.leak_guard = leak_guard or SolutionLeakGuard()

    def generate_hint(
        self,
        hint_level: int,
        misconception_code: str,
        reference_solution: str,
        problem_title: str = "",
        evidence_lines: list[int] | None = None,
        student_code: str = "",
        taxonomy_remedy: str = "",
        taxonomy_name: str = "",
    ) -> GeneratedHint:
        """Generate a progressive hint for hint_level (1..5) with SolutionLeakGuard validation."""
        if hint_level < 1 or hint_level > 5:
            raise ValueError(f"hint_level must be between 1 and 5, got {hint_level}")

        tier_name = TIER_NAMES[hint_level]
        penalty = TIER_PENALTIES[hint_level]

        # Extract evidence callout string if evidence lines exist
        evidence_callout = ""
        if evidence_lines and student_code:
            code_lines = student_code.splitlines()
            target_line_num = evidence_lines[0]
            if 1 <= target_line_num <= len(code_lines):
                target_code = code_lines[target_line_num - 1].strip()
                evidence_callout = (
                    f"Faulty construct on Line {target_line_num}:\n"
                    f"```python\n{target_code}\n```"
                )
            else:
                evidence_callout = f"Check Line {target_line_num} in your submission."
        elif evidence_lines:
            evidence_callout = f"Check Line {evidence_lines[0]} in your submission."

        # Fetch canonical template for misconception code and level
        templates_for_code = HINT_TEMPLATES.get(misconception_code)
        if templates_for_code and hint_level in templates_for_code:
            template = templates_for_code[hint_level]
            raw_title = template["title"]
            raw_content = (
                template["content"]
                .replace("{problem_title}", problem_title or "this problem")
                .replace(
                    "{evidence_callout}",
                    evidence_callout or "Inspect your loop and conditional structure.",
                )
            )
        else:
            # Generic fallback template across 5 tiers
            raw_title, raw_content = self._build_generic_tier(
                hint_level=hint_level,
                misconception_code=misconception_code,
                taxonomy_name=taxonomy_name,
                taxonomy_remedy=taxonomy_remedy,
                evidence_callout=evidence_callout,
            )

        # Pipe through SolutionLeakGuard firewall
        leak_res = self.leak_guard.check_leak(raw_content, reference_solution)

        if leak_res.is_leaked:
            logger.warning(
                "SolutionLeakGuard blocked hint (level %d, code %s, severity %.2f): %s",
                hint_level,
                misconception_code,
                leak_res.severity_score,
                leak_res.leak_reasons,
            )
            # Unconditionally safe conceptual fallback
            safe_title = f"Pedagogical Guidance: {taxonomy_name or misconception_code}"
            safe_remedy = (
                taxonomy_remedy
                or "Review your loop boundaries, variable initialization, and return statements."
            )
            safe_content = (
                f"### Conceptual Guidance for {taxonomy_name or misconception_code}\n\n"
                f"Direct code suggestions have been restricted to protect learning integrity.\n\n"
                f"**Key Principle to Consider:**\n"
                f"{safe_remedy}\n\n"
                f"{evidence_callout}"
            )
            return GeneratedHint(
                hint_level=hint_level,
                hint_tier_name=tier_name,
                hint_title=safe_title,
                hint_content=safe_content,
                penalty_score=penalty,
                leak_check_passed=False,
                leak_severity=leak_res.severity_score,
                fallback_used=True,
            )

        return GeneratedHint(
            hint_level=hint_level,
            hint_tier_name=tier_name,
            hint_title=raw_title,
            hint_content=raw_content,
            penalty_score=penalty,
            leak_check_passed=True,
            leak_severity=leak_res.severity_score,
            fallback_used=False,
        )

    def _build_generic_tier(
        self,
        hint_level: int,
        misconception_code: str,
        taxonomy_name: str,
        taxonomy_remedy: str,
        evidence_callout: str,
    ) -> tuple[str, str]:
        """Generate safe fallback text for any taxonomy class without custom templates."""
        name = taxonomy_name or f"Misconception {misconception_code}"
        remedy = taxonomy_remedy or "Verify algorithmic logic and boundaries."

        if hint_level == 1:
            title = f"Nudge: {name}"
            content = (
                f"Consider how your algorithm handles edge cases for **{name}**.\n\n"
                "What assumption might your code be making that fails under certain inputs?"
            )
        elif hint_level == 2:
            title = f"Conceptual Explanation: {name}"
            content = (
                f"### Core Computing Principle: {name}\n\n"
                f"{remedy}\n\n"
                "Take a moment to verify how data flows through your functions."
            )
        elif hint_level == 3:
            title = "Minimal Edge-Case Consideration"
            content = (
                "Test your program against edge boundaries: an empty collection, a single element, "
                "or duplicate inputs.\n\n"
                "Does your implementation behave as expected on those boundaries?"
            )
        elif hint_level == 4:
            title = "Pattern Analogue"
            content = (
                f"When resolving **{name}**, programmers ensure that all state transitions "
                "preserve the required invariants throughout execution.\n\n"
                f"{remedy}"
            )
        else:  # Level 5
            title = "Targeted Pointer"
            content = (
                f"{evidence_callout}\n\n"
                f"Carefully examine this construct. Apply this guidance:\n\n"
                f"> {remedy}"
            )

        return title, content
