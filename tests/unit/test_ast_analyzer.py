"""Unit tests for AST Analysis Visitor (ml/ast_analyzer.py)."""

from ml.ast_analyzer import extract_structural_facts


def test_ast_analyzer_syntax_error():
    """Verify syntax error is captured cleanly without crashing."""
    broken_code = "def foo(\n    print('broken'\n"
    facts = extract_structural_facts(broken_code)
    assert not facts.syntax.is_valid
    assert facts.syntax.error_line is not None
    assert facts.syntax.error_message is not None


def test_ast_analyzer_loop_facts():
    """Verify loop structure, range calls, and unconditional returns."""
    code = """def search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
        return -1
"""
    facts = extract_structural_facts(code)
    assert facts.syntax.is_valid
    assert len(facts.loops) == 1
    loop = facts.loops[0]
    assert loop.loop_type == "for"
    assert loop.target_vars == ["i"]
    assert loop.is_range_call is True
    assert loop.range_uses_len is True
    assert loop.has_unconditional_return is True
    assert len(loop.unconditional_return_lines) == 1


def test_ast_analyzer_while_loop_facts():
    """Verify while loop condition variables and mutation tracking."""
    code = """def infinite_spin():
    count = 0
    while count < 10:
        print("spinning")
"""
    facts = extract_structural_facts(code)
    assert len(facts.loops) == 1
    loop = facts.loops[0]
    assert loop.loop_type == "while"
    assert "count" in loop.condition_vars
    assert loop.condition_mutated_in_body is False


def test_ast_analyzer_mutable_defaults():
    """Verify detection of mutable default parameters."""
    code = """def append_item(val, items=[], config={}):
    items.append(val)
    return items
"""
    facts = extract_structural_facts(code)
    assert len(facts.functions) == 1
    fn = facts.functions[0]
    assert len(fn.mutable_defaults) == 2
    types = {d.default_type for d in fn.mutable_defaults}
    assert "list" in types
    assert "dict" in types


def test_ast_analyzer_return_placement():
    """Verify return placement inside vs outside loop."""
    code = """def sum_list(items):
    total = 0
    for x in items:
        total += x
    return total
"""
    facts = extract_structural_facts(code)
    fn = facts.functions[0]
    assert fn.has_explicit_return is True
    assert fn.returns_with_value is True
    assert len(fn.returns) == 1
    assert fn.returns[0].is_inside_loop is False


def test_ast_analyzer_subscript_and_assignment():
    """Verify subscript expressions and assignment targets."""
    code = """s = "hello"
s[0] = 'H'
x = arr[len(arr) + 1]
"""
    facts = extract_structural_facts(code)
    assert len(facts.subscripts) == 2
    s0 = facts.subscripts[0]
    assert s0.target_name == "s"
    assert s0.is_assignment_target is True

    s1 = facts.subscripts[1]
    assert s1.target_name == "arr"
    assert s1.index_uses_len is True
    assert s1.index_offset == 1


def test_ast_analyzer_calls_and_builtins():
    """Verify tracking of print and input calls."""
    code = """def greet():
    name = input()
    print("Hello", name)
"""
    facts = extract_structural_facts(code)
    assert len(facts.calls) == 2
    calls = {c.func_name for c in facts.calls}
    assert "input" in calls
    assert "print" in calls
    assert facts.functions[0].calls_print is True


def test_ast_analyzer_variable_read_before_write():
    """Verify identifier usage before definition."""
    code = """def calc():
    total += 5
    total = 0
"""
    facts = extract_structural_facts(code)
    var_facts = {v.name: v for v in facts.variables}
    assert "total" in var_facts
    assert var_facts["total"].read_before_write is True
