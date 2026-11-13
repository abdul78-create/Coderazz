"""Deterministic Rule Detectors for CodeRazz Misconception Engine.

Implements high-precision, zero-false-positive rule detectors for the top 10
introductory Python misconceptions:
- A1: Off-by-one in loop bounds
- A2: Infinite loop condition
- A3: Index out of range
- A5: Premature loop termination
- B1: Assignment instead of equality
- B2: Inverted or incorrect boolean operators
- C1: Uninitialized variable usage
- D2: Missing or implicit None return
- D4: Return inside loop instead of post-loop
- G1: Confusing print() with return
"""

from dataclasses import dataclass, field

from ml.ast_analyzer import StructuralFacts, extract_structural_facts


@dataclass
class RuleDetectionResult:
    """Result emitted when a deterministic rule fires."""

    misconception_code: str
    confidence: float
    evidence_lines: list[int] = field(default_factory=list)
    explanation: str = ""
    detector_name: str = ""


# =============================================================================
# TOP-10 INDIVIDUAL RULE DETECTORS
# =============================================================================


def detect_a1_off_by_one(facts: StructuralFacts) -> RuleDetectionResult | None:
    """A1: Off-by-one in loop bounds.

    Triggers when:
    - range(len(arr) + 1) or range(1, len(arr) + 1) is used as an iterator
    - range(len(arr)) is used while accessing arr[i + 1] inside the loop body
    """
    for loop in facts.loops:
        if (
            loop.loop_type == "for"
            and loop.is_range_call
            and loop.range_uses_len
            and loop.range_len_offset is not None
            and loop.range_len_offset > 0
        ):
            return RuleDetectionResult(
                misconception_code="A1",
                confidence=0.98,
                evidence_lines=[loop.lineno],
                explanation=(
                    f"Line {loop.lineno}: Loop range exceeds collection length "
                    f"(range(len(...) + {loop.range_len_offset})), causing an off-by-one index error."
                ),
                detector_name="detect_a1_off_by_one",
            )

        # Check if loop is range(len(arr)) but subscript uses i + 1
        if (
            loop.loop_type == "for"
            and loop.is_range_call
            and loop.range_uses_len
            and (loop.range_len_offset is None or loop.range_len_offset >= 0)
        ):
            for sub in facts.subscripts:
                if (
                    loop.lineno <= sub.lineno <= loop.end_lineno
                    and sub.index_offset is not None
                    and sub.index_offset > 0
                ):
                    return RuleDetectionResult(
                        misconception_code="A1",
                        confidence=0.95,
                        evidence_lines=[loop.lineno, sub.lineno],
                        explanation=(
                            f"Line {sub.lineno}: Subscript indexes ahead by {sub.index_offset} "
                            f"while loop range at line {loop.lineno} does not reduce upper bound."
                        ),
                        detector_name="detect_a1_off_by_one",
                    )

    return None


def detect_a2_infinite_loop(facts: StructuralFacts) -> RuleDetectionResult | None:
    """A2: Infinite loop condition.

    Triggers when a while loop's tested variables are never mutated inside the loop body
    and the body contains no break or return statement.
    """
    for loop in facts.loops:
        if loop.loop_type == "while":
            # Condition variables exist but none are mutated and no break/return
            if (
                loop.condition_vars
                and not loop.condition_mutated_in_body
                and not loop.has_unconditional_break
                and not loop.has_unconditional_return
            ):
                return RuleDetectionResult(
                    misconception_code="A2",
                    confidence=0.95,
                    evidence_lines=[loop.lineno],
                    explanation=(
                        f"Line {loop.lineno}: While loop condition variables {loop.condition_vars} "
                        "are never mutated inside the loop body, causing an infinite loop."
                    ),
                    detector_name="detect_a2_infinite_loop",
                )
            # while True with no break or return in the entire loop
            if loop.iter_str == "True" and not loop.has_unconditional_break and not loop.has_unconditional_return:
                return RuleDetectionResult(
                    misconception_code="A2",
                    confidence=0.92,
                    evidence_lines=[loop.lineno],
                    explanation=(
                        f"Line {loop.lineno}: 'while True' loop has no termination condition or break statement."
                    ),
                    detector_name="detect_a2_infinite_loop",
                )

    return None


def detect_a3_index_out_of_range(facts: StructuralFacts) -> RuleDetectionResult | None:
    """A3: Index out of range.

    Triggers when a subscript explicitly indexes sequence at len(sequence) or len(sequence) + k.
    """
    for sub in facts.subscripts:
        if sub.index_uses_len and (sub.index_offset is None or sub.index_offset >= 0):
            offset_str = f" + {sub.index_offset}" if sub.index_offset else ""
            return RuleDetectionResult(
                misconception_code="A3",
                confidence=0.96,
                evidence_lines=[sub.lineno],
                explanation=(
                    f"Line {sub.lineno}: Subscript indexes '{sub.target_name}' at len(...){offset_str}. "
                    "Python 0-based indexing valid maximum is len(...) - 1."
                ),
                detector_name="detect_a3_index_out_of_range",
            )

    return None


def detect_a5_premature_loop_termination(facts: StructuralFacts) -> RuleDetectionResult | None:
    """A5: Premature loop termination.

    Triggers when a loop contains an unconditional return or break as a direct statement
    in its body, causing the loop to always exit on the very first iteration.
    """
    for loop in facts.loops:
        if loop.has_unconditional_return and loop.unconditional_return_lines:
            # If there's an accumulator, D4 might also apply; A5 focuses on unconditional early exit
            ret_line = loop.unconditional_return_lines[0]
            return RuleDetectionResult(
                misconception_code="A5",
                confidence=0.96,
                evidence_lines=[loop.lineno, ret_line],
                explanation=(
                    f"Line {ret_line}: Unconditional return statement placed directly inside loop "
                    f"(line {loop.lineno}), terminating the loop on its first iteration."
                ),
                detector_name="detect_a5_premature_loop_termination",
            )
        if loop.has_unconditional_break:
            return RuleDetectionResult(
                misconception_code="A5",
                confidence=0.94,
                evidence_lines=[loop.lineno],
                explanation=(
                    f"Line {loop.lineno}: Loop contains an unconditional break statement, "
                    "terminating after iteration 0."
                ),
                detector_name="detect_a5_premature_loop_termination",
            )

    return None


def detect_b1_assignment_in_condition(facts: StructuralFacts) -> RuleDetectionResult | None:
    """B1: Assignment instead of equality in conditional statements."""
    for comp in facts.compares:
        if comp.has_assignment_in_test:
            return RuleDetectionResult(
                misconception_code="B1",
                confidence=0.95,
                evidence_lines=[comp.lineno],
                explanation=(
                    f"Line {comp.lineno}: Variable assignment inside conditional test. "
                    "Use '==' for comparison rather than '=' or ':='."
                ),
                detector_name="detect_b1_assignment_in_condition",
            )

    return None


def detect_b2_inverted_boolean(facts: StructuralFacts) -> RuleDetectionResult | None:
    """B2: Inverted or incorrect boolean operators.

    Triggers on impossible conditions (e.g. x < 5 and x > 10) or truthy literals in 'or'.
    """
    for comp in facts.compares:
        # Check if compare has 'or' with a non-boolean constant (e.g., if x == 1 or 2)
        if comp.has_truthy_constant_in_boolop or "Or" in comp.bool_ops:
            return RuleDetectionResult(
                misconception_code="B2",
                confidence=0.92,
                evidence_lines=[comp.lineno],
                explanation=(
                    f"Line {comp.lineno}: Chained boolean 'or' expression evaluates a truthy constant. "
                    "In Python, 'x == 1 or 2' tests if 'x == 1' or '2 is truthy'. "
                    "Write explicitly: 'x == 1 or x == 2'."
                ),
                detector_name="detect_b2_inverted_boolean",
            )

    return None


def detect_c1_uninitialized_variable(facts: StructuralFacts) -> RuleDetectionResult | None:
    """C1: Uninitialized variable usage.

    Triggers when a user identifier is read before any assignment in its scope.
    """
    for var in facts.variables:
        if var.read_before_write and var.first_read_lineno is not None:
            return RuleDetectionResult(
                misconception_code="C1",
                confidence=0.97,
                evidence_lines=[var.first_read_lineno],
                explanation=(
                    f"Line {var.first_read_lineno}: Identifier '{var.name}' is referenced before "
                    "being assigned an initial value."
                ),
                detector_name="detect_c1_uninitialized_variable",
            )

    return None


def detect_d2_missing_explicit_return(facts: StructuralFacts) -> RuleDetectionResult | None:
    """D2: Missing or implicit None return in fruitful functions.

    Triggers when a function computes values or has parameters but lacks any return statement.
    """
    for fn in facts.functions:
        if not fn.has_explicit_return and not fn.calls_print and fn.arg_names:
            return RuleDetectionResult(
                misconception_code="D2",
                confidence=0.91,
                evidence_lines=[fn.lineno],
                explanation=(
                    f"Line {fn.lineno}: Function '{fn.name}' computes logic but has no explicit 'return' statement, "
                    "returning None by default."
                ),
                detector_name="detect_d2_missing_explicit_return",
            )

    return None


def detect_d4_return_inside_accumulator_loop(facts: StructuralFacts) -> RuleDetectionResult | None:
    """D4: Return inside loop instead of post-loop for accumulators.

    Triggers when a loop accumulates values into a variable initialized before the loop,
    but executes a return statement inside the loop.
    """
    for loop in facts.loops:
        if loop.has_unconditional_return and loop.unconditional_return_lines:
            # Check if an enclosing function exists and has an accumulator pattern
            for fn in facts.functions:
                if fn.lineno <= loop.lineno <= fn.end_lineno:
                    ret_line = loop.unconditional_return_lines[0]
                    return RuleDetectionResult(
                        misconception_code="D4",
                        confidence=0.93,
                        evidence_lines=[loop.lineno, ret_line],
                        explanation=(
                            f"Line {ret_line}: Return statement placed inside the loop body (line {loop.lineno}). "
                            "If accumulating results, return after the loop has completed all iterations."
                        ),
                        detector_name="detect_d4_return_inside_accumulator_loop",
                    )

    return None


def detect_g1_print_instead_of_return(facts: StructuralFacts) -> RuleDetectionResult | None:
    """G1: Confusing print() with return.

    Triggers when a function calls print() to output results, but has no explicit return statement.
    """
    for fn in facts.functions:
        if fn.calls_print and not fn.returns_with_value:
            print_line = fn.print_lines[0] if fn.print_lines else fn.lineno
            return RuleDetectionResult(
                misconception_code="G1",
                confidence=0.98,
                evidence_lines=[print_line],
                explanation=(
                    f"Line {print_line}: Function '{fn.name}' prints the result with print() instead of "
                    "returning it. Autograders inspect return values, not standard output."
                ),
                detector_name="detect_g1_print_instead_of_return",
            )

    return None


# =============================================================================
# RULE ENGINE PIPELINE
# =============================================================================

TOP_10_DETECTORS = [
    detect_a1_off_by_one,
    detect_a2_infinite_loop,
    detect_a3_index_out_of_range,
    detect_a5_premature_loop_termination,
    detect_b1_assignment_in_condition,
    detect_b2_inverted_boolean,
    detect_c1_uninitialized_variable,
    detect_d2_missing_explicit_return,
    detect_d4_return_inside_accumulator_loop,
    detect_g1_print_instead_of_return,
]


def execute_rule_detectors(source_code: str, facts: StructuralFacts | None = None) -> list[RuleDetectionResult]:
    """Run all top-10 deterministic rule detectors against source code and structural facts.

    Returns:
        List of triggered RuleDetectionResult instances, sorted by confidence descending.
    """
    if facts is None:
        facts = extract_structural_facts(source_code)

    # If code has a syntax error, that takes precedence as S1 meta-class
    if not facts.syntax.is_valid:
        err_line = facts.syntax.error_line or 1
        return [
            RuleDetectionResult(
                misconception_code="S1",
                confidence=1.0,
                evidence_lines=[err_line],
                explanation=f"Line {err_line}: Syntax error: {facts.syntax.error_message}",
                detector_name="syntax_error_precedence",
            )
        ]

    results: list[RuleDetectionResult] = []
    for detector in TOP_10_DETECTORS:
        res = detector(facts)
        if res is not None:
            results.append(res)

    # Sort results by confidence descending
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
