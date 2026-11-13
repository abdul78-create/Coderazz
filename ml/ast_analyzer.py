"""AST Analysis Visitor for CodeRazz Misconception Detection Engine.

Extracts raw structural facts from Python source code:
- Loop boundaries, range calls, and condition mutation
- Return placements (inside vs outside loops, unconditional vs guarded)
- Identifier scopes, uninitialized variable reads, and loop variable rebinding
- Mutable default arguments in function definitions
- Subscripts, index expressions, and mutation targets
- Comparison operators, assignment in condition, and boolean operations
- Function calls (print vs return, input without type conversion, collection mutations)

Decoupled from probability weighting; returns raw structural evidence.
"""

import ast
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SyntaxFact:
    """Syntax validity of the analyzed code."""

    is_valid: bool = True
    error_line: int | None = None
    error_column: int | None = None
    error_message: str | None = None


@dataclass
class LoopFact:
    """Structural facts about a loop construct (for / while)."""

    loop_type: str  # "for" | "while"
    lineno: int
    end_lineno: int
    target_vars: list[str] = field(default_factory=list)
    iter_str: str = ""
    is_range_call: bool = False
    range_args_count: int = 0
    range_uses_len: bool = False
    range_len_offset: int | None = None  # e.g., -1 in range(len(arr) - 1), +1 in len + 1
    condition_vars: list[str] = field(default_factory=list)
    mutated_vars_in_body: list[str] = field(default_factory=list)
    condition_mutated_in_body: bool = False
    has_unconditional_return: bool = False
    has_unconditional_break: bool = False
    unconditional_return_lines: list[int] = field(default_factory=list)
    guarded_return_lines: list[int] = field(default_factory=list)
    nested_depth: int = 0
    rebound_target_vars: list[str] = field(default_factory=list)
    accumulators_initialized_inside: list[str] = field(default_factory=list)


@dataclass
class ReturnFact:
    """Structural facts about a return statement."""

    lineno: int
    has_value: bool
    value_str: str
    is_inside_loop: bool
    is_unconditional_in_loop: bool
    enclosing_func: str | None = None


@dataclass
class MutableDefaultFact:
    """Structural fact for mutable default parameter."""

    arg_name: str
    lineno: int
    default_type: str  # "list" | "dict" | "set"


@dataclass
class FunctionFact:
    """Structural facts about a function definition."""

    name: str
    lineno: int
    end_lineno: int
    arg_names: list[str] = field(default_factory=list)
    mutable_defaults: list[MutableDefaultFact] = field(default_factory=list)
    returns: list[ReturnFact] = field(default_factory=list)
    has_explicit_return: bool = False
    returns_with_value: bool = False
    calls_print: bool = False
    print_lines: list[int] = field(default_factory=list)
    is_recursive: bool = False
    recursive_call_lines: list[int] = field(default_factory=list)


@dataclass
class CompareFact:
    """Structural facts about conditional comparisons."""

    lineno: int
    ops: list[str] = field(default_factory=list)
    left_str: str = ""
    comparators_str: list[str] = field(default_factory=list)
    has_assignment_in_test: bool = False
    bool_ops: list[str] = field(default_factory=list)  # "And" | "Or" | "Not"
    has_truthy_constant_in_boolop: bool = False


@dataclass
class SubscriptFact:
    """Structural facts about indexing and slicing expressions."""

    lineno: int
    target_name: str
    index_str: str
    is_assignment_target: bool = False  # e.g. s[0] = 'a'
    index_uses_len: bool = False
    index_offset: int | None = None


@dataclass
class CallFact:
    """Structural facts about function and method invocations."""

    lineno: int
    func_name: str
    caller_name: str | None = None
    args_count: int = 0
    is_print_call: bool = False
    is_input_call: bool = False
    input_is_unparsed: bool = False
    is_collection_mutation: bool = False
    mutation_method: str | None = None


@dataclass
class VariableFact:
    """Structural facts about variable declarations and scope usage."""

    name: str
    first_read_lineno: int | None = None
    first_write_lineno: int | None = None
    read_before_write: bool = False
    written_in_loop: bool = False


@dataclass
class StructuralFacts:
    """Aggregated structural facts extracted by the AST analyzer."""

    syntax: SyntaxFact = field(default_factory=SyntaxFact)
    loops: list[LoopFact] = field(default_factory=list)
    functions: list[FunctionFact] = field(default_factory=list)
    compares: list[CompareFact] = field(default_factory=list)
    subscripts: list[SubscriptFact] = field(default_factory=list)
    calls: list[CallFact] = field(default_factory=list)
    variables: list[VariableFact] = field(default_factory=list)
    ast_node_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert facts to serializable dictionary."""
        return asdict(self)


class CodeStructuralVisitor(ast.NodeVisitor):
    """Visitor that extracts raw structural facts from a Python AST."""

    def __init__(self, source_code: str) -> None:
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.facts = StructuralFacts()

        # Scope and traversal tracking stacks
        self._loop_stack: list[ast.AST] = []
        self._func_stack: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        self._loop_depth: int = 0
        self._var_first_reads: dict[str, int] = {}
        self._var_first_writes: dict[str, int] = {}
        self._assigned_vars_so_far: set[str] = set()
        self._read_before_write_vars: set[str] = set()
        self._written_in_loop: set[str] = set()

    def analyze(self) -> StructuralFacts:
        """Parse source code and extract structural facts."""
        try:
            tree = ast.parse(self.source_code)
        except SyntaxError as err:
            self.facts.syntax = SyntaxFact(
                is_valid=False,
                error_line=err.lineno,
                error_column=err.offset,
                error_message=str(err.msg),
            )
            return self.facts

        self.visit(tree)
        self._finalize_variable_facts()
        return self.facts

    def visit(self, node: ast.AST) -> None:
        """Count AST node types and dispatch to visitors."""
        node_type = type(node).__name__
        self.facts.ast_node_counts[node_type] = (
            self.facts.ast_node_counts.get(node_type, 0) + 1
        )
        super().visit(node)

    # -------------------------------------------------------------------------
    # FUNCTION DEFINITIONS & RETURNS
    # -------------------------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_func(node)

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        func_fact = FunctionFact(
            name=node.name,
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            arg_names=[a.arg for a in node.args.args],
        )

        # Check mutable default parameter values
        defaults = node.args.defaults
        non_default_count = len(node.args.args) - len(defaults)
        for idx, default_node in enumerate(defaults):
            arg_name = node.args.args[non_default_count + idx].arg
            if isinstance(default_node, ast.List):
                func_fact.mutable_defaults.append(
                    MutableDefaultFact(arg_name=arg_name, lineno=default_node.lineno, default_type="list")
                )
            elif isinstance(default_node, ast.Dict):
                func_fact.mutable_defaults.append(
                    MutableDefaultFact(arg_name=arg_name, lineno=default_node.lineno, default_type="dict")
                )
            elif isinstance(default_node, ast.Set):
                func_fact.mutable_defaults.append(
                    MutableDefaultFact(arg_name=arg_name, lineno=default_node.lineno, default_type="set")
                )

        # Register function arguments as defined
        for a in node.args.args:
            self._assigned_vars_so_far.add(a.arg)

        self._func_stack.append(node)
        self.facts.functions.append(func_fact)

        # Generic visit to children
        self.generic_visit(node)

        self._func_stack.pop()

    def visit_Return(self, node: ast.Return) -> None:
        is_inside_loop = len(self._loop_stack) > 0
        is_unconditional = False

        if is_inside_loop:
            innermost_loop = self._loop_stack[-1]
            # If the return statement is a direct child of the loop body
            if node in innermost_loop.body:
                is_unconditional = True

        val_str = ""
        if node.value is not None:
            try:
                val_str = ast.unparse(node.value)
            except (ValueError, TypeError, AttributeError):
                val_str = "<expr>"

        enclosing_func_name = self._func_stack[-1].name if self._func_stack else None

        ret_fact = ReturnFact(
            lineno=node.lineno,
            has_value=node.value is not None,
            value_str=val_str,
            is_inside_loop=is_inside_loop,
            is_unconditional_in_loop=is_unconditional,
            enclosing_func=enclosing_func_name,
        )

        if self.facts.functions:
            curr_func = self.facts.functions[-1]
            curr_func.returns.append(ret_fact)
            curr_func.has_explicit_return = True
            if node.value is not None:
                curr_func.returns_with_value = True

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # LOOPS (FOR & WHILE)
    # -------------------------------------------------------------------------

    def visit_For(self, node: ast.For) -> None:
        self._loop_depth += 1
        self._loop_stack.append(node)

        # Extract target variable names
        target_vars: list[str] = []
        if isinstance(node.target, ast.Name):
            target_vars.append(node.target.id)
        elif isinstance(node.target, (ast.Tuple, ast.List)):
            for elt in node.target.elts:
                if isinstance(elt, ast.Name):
                    target_vars.append(elt.id)

        iter_str = ""
        try:
            iter_str = ast.unparse(node.iter)
        except (ValueError, TypeError, AttributeError):
            iter_str = "<iter>"

        is_range = False
        range_args_count = 0
        range_uses_len = False
        range_len_offset: int | None = None

        if isinstance(node.iter, ast.Call):
            func_name = ""
            if isinstance(node.iter.func, ast.Name):
                func_name = node.iter.func.id

            if func_name == "range":
                is_range = True
                range_args_count = len(node.iter.args)
                # Check if len(...) is inside the range args
                for arg in node.iter.args:
                    arg_str = ast.unparse(arg)
                    if "len(" in arg_str:
                        range_uses_len = True
                        if isinstance(arg, ast.BinOp):
                            if isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant):
                                range_len_offset = -int(arg.right.value)
                            elif isinstance(arg.op, ast.Add) and isinstance(arg.right, ast.Constant):
                                range_len_offset = int(arg.right.value)

        # Body inspection for unconditional returns / breaks
        uncond_returns: list[int] = []
        guarded_returns: list[int] = []
        uncond_breaks = False
        rebound_targets: list[str] = []
        accumulators_in_loop: list[str] = []

        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                uncond_returns.append(stmt.lineno)
            elif isinstance(stmt, ast.Break):
                uncond_breaks = True
            elif isinstance(stmt, (ast.Assign, ast.AugAssign)):
                # Check loop target rebinding or accumulator reset
                assigned_names = self._extract_assigned_names(stmt)
                for name in assigned_names:
                    if name in target_vars:
                        rebound_targets.append(name)
                    # Simple heuristic: if assigning constant to variable that was not in targets
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.value, (ast.Constant, ast.List, ast.Dict))
                    ):
                        accumulators_in_loop.append(name)

        loop_fact = LoopFact(
            loop_type="for",
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            target_vars=target_vars,
            iter_str=iter_str,
            is_range_call=is_range,
            range_args_count=range_args_count,
            range_uses_len=range_uses_len,
            range_len_offset=range_len_offset,
            has_unconditional_return=len(uncond_returns) > 0,
            has_unconditional_break=uncond_breaks,
            unconditional_return_lines=uncond_returns,
            guarded_return_lines=guarded_returns,
            nested_depth=self._loop_depth,
            rebound_target_vars=rebound_targets,
            accumulators_initialized_inside=accumulators_in_loop,
        )
        self.facts.loops.append(loop_fact)

        self.generic_visit(node)

        self._loop_stack.pop()
        self._loop_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._loop_depth += 1
        self._loop_stack.append(node)

        # Extract variables tested in condition
        condition_vars = [n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)]

        # Collect variables mutated inside while body
        mutated_vars: list[str] = []
        uncond_returns: list[int] = []
        uncond_breaks = False

        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                uncond_returns.append(stmt.lineno)
            elif isinstance(stmt, ast.Break):
                uncond_breaks = True
            elif isinstance(stmt, (ast.Assign, ast.AugAssign)):
                mutated_vars.extend(self._extract_assigned_names(stmt))

        # Check if condition variables are modified in the loop body
        cond_mutated = any(v in mutated_vars for v in condition_vars)

        iter_str = ""
        try:
            iter_str = ast.unparse(node.test)
        except (ValueError, TypeError, AttributeError):
            iter_str = "<test>"

        loop_fact = LoopFact(
            loop_type="while",
            lineno=node.lineno,
            end_lineno=getattr(node, "end_lineno", node.lineno),
            iter_str=iter_str,
            condition_vars=condition_vars,
            mutated_vars_in_body=mutated_vars,
            condition_mutated_in_body=cond_mutated,
            has_unconditional_return=len(uncond_returns) > 0,
            has_unconditional_break=uncond_breaks,
            unconditional_return_lines=uncond_returns,
            nested_depth=self._loop_depth,
        )
        self.facts.loops.append(loop_fact)

        self.generic_visit(node)

        self._loop_stack.pop()
        self._loop_depth -= 1

    # -------------------------------------------------------------------------
    # COMPARISONS & CONDITIONALS
    # -------------------------------------------------------------------------

    def visit_Compare(self, node: ast.Compare) -> None:
        ops = [type(op).__name__ for op in node.ops]
        left_str = ""
        try:
            left_str = ast.unparse(node.left)
        except (ValueError, TypeError, AttributeError):
            left_str = "<left>"

        comparators_str = []
        for comp in node.comparators:
            try:
                comparators_str.append(ast.unparse(comp))
            except (ValueError, TypeError, AttributeError):
                comparators_str.append("<comp>")

        self.facts.compares.append(
            CompareFact(
                lineno=node.lineno,
                ops=ops,
                left_str=left_str,
                comparators_str=comparators_str,
            )
        )
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        op_name = type(node.op).__name__
        has_truthy = any(
            isinstance(v, ast.Constant) and v.value not in (True, False, None)
            for v in node.values
        )
        if has_truthy:
            self.facts.compares.append(
                CompareFact(
                    lineno=node.lineno,
                    bool_ops=[op_name],
                    has_truthy_constant_in_boolop=True,
                )
            )
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        # Check if condition uses assignment (walrus operator)
        has_named_expr = any(isinstance(n, ast.NamedExpr) for n in ast.walk(node.test))

        bool_ops: list[str] = []
        for n in ast.walk(node.test):
            if isinstance(n, ast.BoolOp):
                bool_ops.append(type(n.op).__name__)

        if has_named_expr:
            self.facts.compares.append(
                CompareFact(
                    lineno=node.lineno,
                    has_assignment_in_test=True,
                    bool_ops=bool_ops,
                )
            )

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # SUBSCRIPTS & INDEXING
    # -------------------------------------------------------------------------

    def visit_Subscript(self, node: ast.Subscript) -> None:
        target_name = ""
        if isinstance(node.value, ast.Name):
            target_name = node.value.id
        elif isinstance(node.value, ast.Attribute):
            target_name = getattr(node.value, "attr", "<attr>")

        index_str = ""
        try:
            index_str = ast.unparse(node.slice)
        except (ValueError, TypeError, AttributeError):
            index_str = "<slice>"

        index_uses_len = "len(" in index_str
        index_offset = None
        if isinstance(node.slice, ast.BinOp):
            if isinstance(node.slice.op, ast.Add) and isinstance(node.slice.right, ast.Constant):
                index_offset = int(node.slice.right.value)
            elif isinstance(node.slice.op, ast.Sub) and isinstance(node.slice.right, ast.Constant):
                index_offset = -int(node.slice.right.value)

        # Check if this subscript is an assignment target (e.g. s[0] = 'a')
        is_target = isinstance(node.ctx, ast.Store)

        self.facts.subscripts.append(
            SubscriptFact(
                lineno=node.lineno,
                target_name=target_name,
                index_str=index_str,
                is_assignment_target=is_target,
                index_uses_len=index_uses_len,
                index_offset=index_offset,
            )
        )
        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # CALLS & BUILTINS
    # -------------------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        caller_name: str | None = None

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                caller_name = node.func.value.id

        is_print = func_name == "print"
        is_input = func_name == "input"

        # Check collection mutation calls (e.g., list.append, list.remove, list.pop)
        mutation_methods = {"append", "extend", "insert", "remove", "pop", "clear"}
        is_mutation = func_name in mutation_methods and caller_name is not None

        call_fact = CallFact(
            lineno=node.lineno,
            func_name=func_name,
            caller_name=caller_name,
            args_count=len(node.args),
            is_print_call=is_print,
            is_input_call=is_input,
            is_collection_mutation=is_mutation,
            mutation_method=func_name if is_mutation else None,
        )
        self.facts.calls.append(call_fact)

        if self.facts.functions:
            curr_func = self.facts.functions[-1]
            if is_print:
                curr_func.calls_print = True
                curr_func.print_lines.append(node.lineno)
            if func_name == curr_func.name:
                curr_func.is_recursive = True
                curr_func.recursive_call_lines.append(node.lineno)

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # VARIABLE SCOPE & ASSIGNMENT TRACKING
    # -------------------------------------------------------------------------

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if isinstance(node.target, ast.Name):
            if node.target.id not in self._var_first_reads:
                self._var_first_reads[node.target.id] = node.lineno
            if node.target.id not in self._assigned_vars_so_far:
                self._read_before_write_vars.add(node.target.id)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            if node.id not in self._var_first_writes:
                self._var_first_writes[node.id] = node.lineno
            self._assigned_vars_so_far.add(node.id)
            if self._loop_depth > 0:
                self._written_in_loop.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            if node.id not in self._var_first_reads:
                self._var_first_reads[node.id] = node.lineno
            if node.id not in self._assigned_vars_so_far:
                self._read_before_write_vars.add(node.id)

        self.generic_visit(node)

    def _finalize_variable_facts(self) -> None:
        all_vars = set(self._var_first_reads.keys()) | set(self._var_first_writes.keys())
        # Filter out built-ins and standard keywords
        builtins = {
            "print", "range", "len", "int", "str", "float", "list", "dict", "set",
            "tuple", "enumerate", "zip", "min", "max", "sum", "sorted", "reversed",
            "True", "False", "None", "self",
        }

        for var_name in sorted(all_vars - builtins):
            r_line = self._var_first_reads.get(var_name)
            w_line = self._var_first_writes.get(var_name)
            read_before_write = var_name in self._read_before_write_vars

            self.facts.variables.append(
                VariableFact(
                    name=var_name,
                    first_read_lineno=r_line,
                    first_write_lineno=w_line,
                    read_before_write=read_before_write,
                    written_in_loop=var_name in self._written_in_loop,
                )
            )

    def _extract_assigned_names(self, stmt: ast.AST) -> list[str]:
        names: list[str] = []
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            names.append(stmt.target.id)
        return names


def extract_structural_facts(source_code: str) -> StructuralFacts:
    """Convenience helper to extract structural facts from Python source code."""
    visitor = CodeStructuralVisitor(source_code)
    return visitor.analyze()
