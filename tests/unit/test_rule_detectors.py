"""Unit tests for top-10 deterministic rule detectors (ml/rule_detectors.py)."""

from ml.rule_detectors import execute_rule_detectors


def test_rule_a1_off_by_one():
    code = """def get_last(arr):
    for i in range(len(arr) + 1):
        print(arr[i])
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "A1" in codes
    top = results[0]
    assert top.misconception_code == "A1"
    assert top.confidence >= 0.95
    assert len(top.evidence_lines) > 0


def test_rule_a2_infinite_loop():
    code = """def spin():
    i = 0
    while i < 10:
        print("stuck")
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "A2" in codes
    match = next(r for r in results if r.misconception_code == "A2")
    assert match.confidence >= 0.90


def test_rule_a3_index_out_of_range():
    code = """def last_item(nums):
    return nums[len(nums)]
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "A3" in codes
    match = next(r for r in results if r.misconception_code == "A3")
    assert match.confidence >= 0.95


def test_rule_a5_premature_loop_termination():
    code = """def contains_target(arr, target):
    for x in arr:
        return x == target
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "A5" in codes
    match = next(r for r in results if r.misconception_code == "A5")
    assert match.confidence >= 0.90


def test_rule_b1_assignment_in_condition():
    code = """def check(x):
    if (y := x + 1):
        return True
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "B1" in codes


def test_rule_b2_inverted_boolean():
    code = """def check_val(x):
    if x == 1 or 2:
        return True
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "B2" in codes


def test_rule_c1_uninitialized_variable():
    code = """def sum_items(nums):
    total += 1
    total = 0
    return total
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "C1" in codes
    match = next(r for r in results if r.misconception_code == "C1")
    assert match.confidence >= 0.95


def test_rule_d2_missing_explicit_return():
    code = """def compute_area(width, height):
    area = width * height
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "D2" in codes


def test_rule_d4_return_inside_accumulator_loop():
    code = """def total(items):
    s = 0
    for x in items:
        s += x
        return s
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "D4" in codes or "A5" in codes


def test_rule_g1_print_instead_of_return():
    code = """def add(a, b):
    print(a + b)
"""
    results = execute_rule_detectors(code)
    codes = [r.misconception_code for r in results]
    assert "G1" in codes
    match = next(r for r in results if r.misconception_code == "G1")
    assert match.confidence >= 0.95


def test_s1_syntax_error_precedence():
    code = "def broken(\n  x = 1"
    results = execute_rule_detectors(code)
    assert len(results) == 1
    assert results[0].misconception_code == "S1"
    assert results[0].confidence == 1.0


def test_clean_code_no_false_positive():
    code = """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
"""
    results = execute_rule_detectors(code)
    assert len(results) == 0
