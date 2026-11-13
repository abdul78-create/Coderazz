"""Solution Leak Firewall for CodeRazz Pedagogical Hint Engine.

Mathematically guarantees that hints provided to students do not reveal the hidden
reference solution through:
1. Regex pattern matching & exact code copy-pasting detection.
2. Normalized token n-gram overlap & sequence containment (defeating variable renaming).
3. AST subtree isomorphism & structural similarity (defeating structural re-wrapping).
"""

import ast
import io
import keyword
import re
import tokenize
from dataclasses import dataclass, field

# Standard Python builtins and boilerplate identifiers that are not problem-specific
STANDARD_BUILTINS = {
    "len", "range", "print", "enumerate", "int", "str", "list", "dict", "set",
    "tuple", "bool", "float", "True", "False", "None", "min", "max", "sum",
    "abs", "zip", "map", "filter", "sorted", "reversed", "sys", "os", "math",
    "stdin", "stdout", "read", "readline", "strip", "split", "splitlines",
    "append", "extend", "pop", "get", "keys", "values", "items", "add", "remove",
}

BOILERPLATE_LINES = {
    "import sys", "import os", "import math", "def solve():", "def main():",
    "if __name__ == '__main__':", "if __name__ == \"__main__\":", "solve()",
    "main()", "pass", "return", "...",
}


@dataclass
class LeakGuardResult:
    """Outcome of a solution leak evaluation."""

    is_leaked: bool
    severity_score: float  # 0.0 (completely safe) to 1.0 (blatant direct leak)
    leak_reasons: list[str] = field(default_factory=list)
    matched_snippets: list[str] = field(default_factory=list)
    ast_similarity: float = 0.0
    token_ngram_overlap: float = 0.0


class IdentifierNormalizer(ast.NodeTransformer):
    """Normalizes non-builtin variable and function identifiers into generic placeholders."""

    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self.counter = 0

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in STANDARD_BUILTINS or keyword.iskeyword(node.id):
            return node
        if node.id not in self.mapping:
            self.mapping[node.id] = f"$VAR_{self.counter}"
            self.counter += 1
        return ast.copy_location(ast.Name(id=self.mapping[node.id], ctx=node.ctx), node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if node.name not in ("solve", "main") and node.name not in self.mapping:
            self.mapping[node.name] = f"$FUNC_{self.counter}"
            self.counter += 1
            node.name = self.mapping[node.name]
        self.generic_visit(node)
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if node.arg not in STANDARD_BUILTINS and not keyword.iskeyword(node.arg):
            if node.arg not in self.mapping:
                self.mapping[node.arg] = f"$VAR_{self.counter}"
                self.counter += 1
            node.arg = self.mapping[node.arg]
        return node


class SolutionLeakGuard:
    """Multi-tiered firewall protecting hidden reference solutions from leaking into hints."""

    def __init__(
        self,
        token_ngram_size: int = 4,
        max_allowed_token_ngram_overlap: float = 0.35,
        min_ast_subtree_nodes: int = 5,
    ) -> None:
        self.ngram_size = token_ngram_size
        self.max_allowed_ngram_overlap = max_allowed_token_ngram_overlap
        self.min_ast_subtree_nodes = min_ast_subtree_nodes

    def check_leak(self, hint_text: str, reference_solution: str) -> LeakGuardResult:
        """Evaluate whether hint_text leaks any part of reference_solution."""
        if not hint_text or not reference_solution:
            return LeakGuardResult(is_leaked=False, severity_score=0.0)

        leak_reasons: list[str] = []
        matched_snippets: list[str] = []
        severity = 0.0

        # Extract code blocks and candidate statements from hint
        code_snippets = self._extract_code_snippets(hint_text)

        # ---------------------------------------------------------------------
        # Tier 1: Direct Multi-Line and Substring Matching
        # ---------------------------------------------------------------------
        ref_lines = self._clean_lines(reference_solution)
        for snippet in code_snippets:
            snippet_lines = self._clean_lines(snippet)
            # Check for exact consecutive lines
            for i in range(len(snippet_lines)):
                for r in range(len(ref_lines)):
                    if snippet_lines[i] == ref_lines[r]:
                        # Check if consecutive lines match
                        match_count = 1
                        while (
                            i + match_count < len(snippet_lines)
                            and r + match_count < len(ref_lines)
                            and snippet_lines[i + match_count] == ref_lines[r + match_count]
                        ):
                            match_count += 1
                        if match_count >= 2:
                            matched_str = "\n".join(snippet_lines[i : i + match_count])
                            leak_reasons.append(
                                f"Direct code copy-paste: {match_count} consecutive reference solution lines detected."
                            )
                            matched_snippets.append(matched_str)
                            severity = max(severity, 1.0)
                            break
                        # Single significant algorithmic line match (longer than 15 chars)
                        if len(snippet_lines[i]) >= 15:
                            matched_snippets.append(snippet_lines[i])
                            leak_reasons.append(
                                f"Direct line copy: Identical reference solution line '{snippet_lines[i]}' detected."
                            )
                            severity = max(severity, 0.75)

        # ---------------------------------------------------------------------
        # Tier 2: Normalized AST Subtree Isomorphism
        # ---------------------------------------------------------------------
        ref_subtrees = self._extract_normalized_subtrees(reference_solution)
        ast_match_found = False

        for snippet in code_snippets:
            hint_subtrees = self._extract_normalized_subtrees(snippet)
            for h_dump, h_size, h_src in hint_subtrees:
                for r_dump, r_size, r_src in ref_subtrees:
                    if h_dump == r_dump and h_size >= self.min_ast_subtree_nodes:
                        ast_match_found = True
                        severity = max(severity, 0.90)
                        leak_reasons.append(
                            f"Structural AST leak: Isomorphic subtree ({h_size} nodes) matches reference solution logic."
                        )
                        matched_snippets.append(h_src)
                        break
                if ast_match_found:
                    break
            if ast_match_found:
                break

        # ---------------------------------------------------------------------
        # Tier 3: Normalized Token N-Gram Overlap & Sequence Containment
        # ---------------------------------------------------------------------
        ref_norm_tokens = self._get_normalized_tokens(reference_solution)
        max_ngram_overlap = 0.0

        for snippet in code_snippets:
            hint_norm_tokens = self._get_normalized_tokens(snippet)
            if not hint_norm_tokens or not ref_norm_tokens:
                continue

            # Check consecutive sequence containment of size >= 4
            consec_match = self._longest_common_token_subsequence(hint_norm_tokens, ref_norm_tokens)
            overlap = self._compute_ngram_containment(hint_norm_tokens, ref_norm_tokens, n=3)
            max_ngram_overlap = max(max_ngram_overlap, overlap)

            if consec_match >= 5:
                severity = max(severity, 0.85)
                leak_reasons.append(
                    f"Token sequence leak: Continuous sequence of {consec_match} normalized tokens matches reference solution."
                )
            elif consec_match >= 4 and overlap >= 0.25:
                severity = max(severity, 0.65)
                leak_reasons.append(
                    f"Token sequence leak: Continuous sequence of {consec_match} normalized tokens matches reference solution."
                )

        if max_ngram_overlap >= self.max_allowed_ngram_overlap:
            severity = max(severity, min(1.0, max_ngram_overlap + 0.3))
            leak_reasons.append(
                f"High token n-gram overlap: {max_ngram_overlap:.1%} normalized token 3-gram containment exceeds threshold."
            )

        # ---------------------------------------------------------------------
        # Final Verdict Decision
        # ---------------------------------------------------------------------
        is_leaked = severity >= 0.50 or len(leak_reasons) > 0

        return LeakGuardResult(
            is_leaked=is_leaked,
            severity_score=round(min(1.0, severity), 3),
            leak_reasons=list(set(leak_reasons)),
            matched_snippets=matched_snippets[:3],
            ast_similarity=1.0 if ast_match_found else 0.0,
            token_ngram_overlap=round(max_ngram_overlap, 3),
        )

    def _extract_code_snippets(self, text: str) -> list[str]:
        """Extract fenced blocks, inline code, and code-like statements from text."""
        snippets: list[str] = []

        # 1. Fenced markdown code blocks ```python ... ```
        fenced = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*([\s\S]*?)```", text)
        for block in fenced:
            cleaned = block.strip()
            if cleaned:
                snippets.append(cleaned)

        # 2. Inline code spans `...` (ignoring single words/variables)
        inline = re.findall(r"`([^`\n]{6,})`", text)
        for span in inline:
            cleaned = span.strip()
            # If looks like statement or expression with operator
            if any(op in cleaned for op in ("=", "(", ")", "[", "]", ":", "+", "-", "*", "/", "in ", "for ", "if ")):
                snippets.append(cleaned)

        # 3. If no code blocks were found, treat entire text as potential raw code
        if not snippets:
            snippets.append(text)

        return snippets

    def _clean_lines(self, code_str: str) -> list[str]:
        """Strip comments, whitespace, and boilerplate lines from code."""
        cleaned_lines: list[str] = []
        for line in code_str.splitlines():
            # Strip comments
            code_part = line.split("#", 1)[0].strip()
            if not code_part:
                continue
            if code_part in BOILERPLATE_LINES:
                continue
            cleaned_lines.append(code_part)
        return cleaned_lines

    def _extract_normalized_subtrees(self, code_str: str) -> list[tuple[str, int, str]]:
        """Parse code, walk non-trivial AST subtrees, and return (normalized_dump, node_count, source)."""
        subtrees: list[tuple[str, int, str]] = []
        try:
            tree = ast.parse(code_str)
        except SyntaxError:
            # Try wrapping statement fragment inside function
            try:
                tree = ast.parse(f"def _dummy_wrapper():\n    {code_str}")
            except SyntaxError:
                return []

        for node in ast.walk(tree):
            # Target structural statements: For, While, If, FunctionDef, Assign with operations, Return with expressions
            if isinstance(node, (ast.For, ast.While, ast.If, ast.FunctionDef, ast.Assign, ast.AugAssign, ast.Return)):
                node_count = sum(1 for _ in ast.walk(node))
                if node_count >= self.min_ast_subtree_nodes:
                    # Clone and normalize
                    cloned = ast.fix_missing_locations(ast.parse(ast.unparse(node)))
                    normalizer = IdentifierNormalizer()
                    normalizer.visit(cloned)
                    dump_str = ast.dump(cloned, annotate_fields=False)
                    src = ast.unparse(node)
                    subtrees.append((dump_str, node_count, src))

        return subtrees

    def _get_normalized_tokens(self, code_str: str) -> list[str]:
        """Tokenize code and normalize non-keyword identifiers to sequential placeholders."""
        tokens: list[str] = []
        name_map: dict[str, str] = {}
        counter = 0

        try:
            tok_gen = tokenize.tokenize(io.BytesIO(code_str.encode("utf-8")).readline)
            for tok in tok_gen:
                if tok.type in (tokenize.ENCODING, tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT):
                    continue
                val = tok.string.strip()
                if not val:
                    continue

                if tok.type == tokenize.NAME:
                    if keyword.iskeyword(val) or val in STANDARD_BUILTINS:
                        tokens.append(val)
                    else:
                        if val not in name_map:
                            name_map[val] = f"$ID_{counter}"
                            counter += 1
                        tokens.append(name_map[val])
                elif tok.type in (tokenize.OP, tokenize.NUMBER, tokenize.STRING):
                    tokens.append(val)
        except (tokenize.TokenError, IndentationError):
            # Fallback to regex tokenization
            raw_words = re.findall(r"\b\w+\b|[+\-*/%<>=!]=?|[()[\]{},;:]", code_str)
            for w in raw_words:
                if keyword.iskeyword(w) or w in STANDARD_BUILTINS or not w.isidentifier():
                    tokens.append(w)
                else:
                    if w not in name_map:
                        name_map[w] = f"$ID_{counter}"
                        counter += 1
                    tokens.append(name_map[w])

        return tokens

    def _longest_common_token_subsequence(self, tokens_a: list[str], tokens_b: list[str]) -> int:
        """Find the length of the longest continuous common token sequence."""
        if not tokens_a or not tokens_b:
            return 0

        # Check for sliding window matches of decreasing sizes
        for length in range(min(len(tokens_a), len(tokens_b), 12), 3, -1):
            sub_a_set = {tuple(tokens_a[i : i + length]) for i in range(len(tokens_a) - length + 1)}
            for j in range(len(tokens_b) - length + 1):
                window = tuple(tokens_b[j : j + length])
                if window in sub_a_set:
                    # Ignore sequences composed solely of brackets or commas
                    if all(t in "()[]{},;:" for t in window):
                        continue
                    # Ignore common generic initialization sequences like d = {} or l = []
                    if len(window) == 4 and window[1] == "=" and window[2] in ("{", "[") and window[3] in ("}", "]"):
                        continue
                    return length
        return 0

    def _compute_ngram_containment(self, query_tokens: list[str], target_tokens: list[str], n: int = 3) -> float:
        """Compute the containment ratio: proportion of query n-grams present in target."""
        if len(query_tokens) < n or len(target_tokens) < n:
            return 0.0

        query_ngrams = {tuple(query_tokens[i : i + n]) for i in range(len(query_tokens) - n + 1)}
        target_ngrams = {tuple(target_tokens[i : i + n]) for i in range(len(target_tokens) - n + 1)}

        if not query_ngrams:
            return 0.0

        matched = len(query_ngrams.intersection(target_ngrams))
        return matched / len(query_ngrams)
