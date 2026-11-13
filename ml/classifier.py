"""Lightweight Scikit-Learn Classifier for CodeRazz Misconception Taxonomy.

Extracts AST node type distributions and token n-grams to estimate a probability
distribution over misconception classes when deterministic rules do not fire.
"""

import ast
from typing import Any

from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from ml.ast_analyzer import extract_structural_facts

# Canonical training exemplars for introductory Python misconceptions
TRAINING_EXEMPLARS: list[dict[str, str]] = [
    # A1: Off-by-one in loop bounds
    {"code": "def loop(arr):\n    for i in range(len(arr) + 1):\n        print(arr[i])", "label": "A1"},
    {"code": "def last(arr):\n    for i in range(1, len(arr) + 1):\n        x = arr[i]", "label": "A1"},
    {"code": "def check(nums):\n    for i in range(len(nums)):\n        if nums[i] == nums[i + 1]: return True", "label": "A1"},

    # A2: Infinite loop condition
    {"code": "def spin():\n    i = 0\n    while i < 10:\n        print('stuck')", "label": "A2"},
    {"code": "def forever():\n    while True:\n        pass", "label": "A2"},
    {"code": "def loop_no_inc(n):\n    while n > 0:\n        print(n)", "label": "A2"},

    # A3: Index out of range
    {"code": "def get_item(arr):\n    return arr[len(arr)]", "label": "A3"},
    {"code": "def bad_idx(nums):\n    idx = len(nums)\n    return nums[idx]", "label": "A3"},
    {"code": "def index_past(s):\n    return s[len(s) + 2]", "label": "A3"},

    # A4: Inner loop variable shadowing
    {"code": "def nested(grid):\n    for i in range(len(grid)):\n        for i in range(len(grid[0])):\n            print(i)", "label": "A4"},
    {"code": "def matrix(m):\n    for r in range(3):\n        for r in range(3):\n            val = m[r][r]", "label": "A4"},

    # A5: Premature loop termination
    {"code": "def contains(arr, x):\n    for item in arr:\n        return item == x", "label": "A5"},
    {"code": "def find(nums, t):\n    for n in nums:\n        if n == t: return True\n        return False", "label": "A5"},

    # B1: Assignment instead of equality
    {"code": "def check(x):\n    if (y := x + 1):\n        return True", "label": "B1"},
    {"code": "def assign_cond(val):\n    if (val := 10):\n        return val", "label": "B1"},

    # B2: Inverted boolean operators
    {"code": "def test_val(x):\n    if x == 1 or 2:\n        return True", "label": "B2"},
    {"code": "def bad_and(score):\n    if score < 0 and score > 100:\n        return False", "label": "B2"},

    # C1: Uninitialized variable
    {"code": "def sum_list(items):\n    total += 1\n    total = 0\n    return total", "label": "C1"},
    {"code": "def count(s):\n    c += 1\n    return c", "label": "C1"},

    # C3: Mutable default argument
    {"code": "def append_val(x, lst=[]):\n    lst.append(x)\n    return lst", "label": "C3"},
    {"code": "def add_config(key, val, cfg={}):\n    cfg[key] = val\n    return cfg", "label": "C3"},

    # D1: Missing recursive base case
    {"code": "def countdown(n):\n    print(n)\n    return countdown(n - 1)", "label": "D1"},
    {"code": "def fact(n):\n    return n * fact(n - 1)", "label": "D1"},

    # D2: Missing explicit return
    {"code": "def area(w, h):\n    res = w * h", "label": "D2"},
    {"code": "def calc_total(items):\n    s = sum(items)", "label": "D2"},

    # D4: Return inside accumulator loop
    {"code": "def sum_arr(arr):\n    s = 0\n    for x in arr:\n        s += x\n        return s", "label": "D4"},
    {"code": "def prod(nums):\n    p = 1\n    for n in nums:\n        p *= n\n        return p", "label": "D4"},

    # E1: Modifying collection during iteration
    {"code": "def remove_evens(nums):\n    for x in nums:\n        if x % 2 == 0: nums.remove(x)\n    return nums", "label": "E1"},
    {"code": "def pop_items(lst):\n    for i in lst:\n        lst.pop()\n    return lst", "label": "E1"},

    # E2: Unchecked dictionary key access
    {"code": "def get_val(d, k):\n    return d[k]", "label": "E2"},

    # F1: Premature accumulator reset
    {"code": "def sum_all(arr):\n    for x in arr:\n        total = 0\n        total += x\n    return total", "label": "F1"},

    # F2: Inefficient quadratic lookup
    {"code": "def find_duplicates(arr):\n    res = []\n    for x in arr:\n        if x in arr: res.append(x)\n    return res", "label": "F2"},

    # G1: Confusing print with return
    {"code": "def add(a, b):\n    print(a + b)", "label": "G1"},
    {"code": "def greet(name):\n    print(f'Hello {name}')", "label": "G1"},

    # G3: In-place string mutation
    {"code": "def replace_char(s):\n    s[0] = 'X'\n    return s", "label": "G3"},
]


class ASTNodeFeatureExtractor:
    """Transforms Python code into AST node frequency distributions."""

    def fit(self, x: list[str], y: Any = None) -> "ASTNodeFeatureExtractor":
        return self

    def transform(self, x: list[str]) -> list[dict[str, float]]:
        features: list[dict[str, float]] = []
        for code in x:
            node_counts: dict[str, float] = {}
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    t = type(node).__name__
                    node_counts[t] = node_counts.get(t, 0.0) + 1.0
            except SyntaxError:
                node_counts["SyntaxErrorNode"] = 1.0

            # Normalize frequencies
            total = sum(node_counts.values()) or 1.0
            norm_counts = {k: v / total for k, v in node_counts.items()}
            features.append(norm_counts)
        return features


class MisconceptionClassifier:
    """Scikit-Learn hybrid pipeline predicting probability distributions across taxonomy classes."""

    def __init__(self) -> None:
        self.pipeline: Pipeline | None = None
        self.classes_: list[str] = []
        self._initialize_and_train()

    def _initialize_and_train(self) -> None:
        """Train the lightweight classifier on benchmark exemplars."""
        codes = [item["code"] for item in TRAINING_EXEMPLARS]
        labels = [item["label"] for item in TRAINING_EXEMPLARS]

        token_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b|[+\-*/%<>=!]=?|[()[\]{},;:]",
            max_features=250,
        )

        ast_features = Pipeline([
            ("extract", ASTNodeFeatureExtractor()),
            ("vectorize", DictVectorizer(sparse=True)),
        ])

        union = FeatureUnion([
            ("tokens", token_vectorizer),
            ("ast_nodes", ast_features),
        ])

        clf = LogisticRegression(
            C=1.0,
            max_iter=500,
            random_state=42,
            solver="lbfgs",
        )

        self.pipeline = Pipeline([
            ("features", union),
            ("clf", clf),
        ])

        self.pipeline.fit(codes, labels)
        self.classes_ = list(clf.classes_)

    def predict_probabilities(self, code: str) -> dict[str, float]:
        """Return probability distribution over misconception classes."""
        if self.pipeline is None:
            self._initialize_and_train()

        # If code has a syntax error, ML probability defers to S1
        facts = extract_structural_facts(code)
        if not facts.syntax.is_valid:
            return {"S1": 1.0}

        probs = self.pipeline.predict_proba([code])[0]
        prob_dict = {str(cls_name): float(prob) for cls_name, prob in zip(self.classes_, probs, strict=False)}
        # Sort descending
        return dict(sorted(prob_dict.items(), key=lambda x: x[1], reverse=True))

    def predict_top(self, code: str, min_confidence: float = 0.20) -> tuple[str, float] | None:
        """Return (top_misconception_code, probability) if exceeding min_confidence."""
        probs = self.predict_probabilities(code)
        if not probs:
            return None
        top_code, top_prob = next(iter(probs.items()))
        if top_prob >= min_confidence:
            return top_code, top_prob
        return None
