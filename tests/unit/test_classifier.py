"""Unit tests for the Scikit-Learn Misconception Classifier."""

import pytest

from ml.classifier import ASTNodeFeatureExtractor, MisconceptionClassifier


@pytest.fixture(scope="module")
def classifier() -> MisconceptionClassifier:
    """Shared trained classifier fixture."""
    return MisconceptionClassifier()


def test_ast_node_feature_extractor() -> None:
    """Test AST node feature extraction and normalization."""
    extractor = ASTNodeFeatureExtractor()
    code_samples = [
        "x = 10\ny = x + 5",
        "for i in range(10):\n    print(i)",
        "def invalid_syntax(:\n    pass",
    ]
    features = extractor.transform(code_samples)

    assert len(features) == 3
    # Check normalization: sums should be approximately 1.0
    for feat in features:
        assert sum(feat.values()) == pytest.approx(1.0, rel=1e-3)

    # Check node types present in python samples
    assert "Assign" in features[0]
    assert "For" in features[1]
    assert "SyntaxErrorNode" in features[2]


def test_classifier_initialization(classifier: MisconceptionClassifier) -> None:
    """Verify that classifier fits and populates classes."""
    assert classifier.pipeline is not None
    assert len(classifier.classes_) > 5
    # Verify core introductory classes are present
    assert "A1" in classifier.classes_
    assert "A2" in classifier.classes_
    assert "A3" in classifier.classes_


def test_classifier_predict_probabilities(classifier: MisconceptionClassifier) -> None:
    """Test probability output format, sorting, and sum."""
    code = "def get_last(arr):\n    return arr[len(arr)]"
    probs = classifier.predict_probabilities(code)

    assert isinstance(probs, dict)
    assert len(probs) == len(classifier.classes_)

    # Verify keys are strings
    for k in probs:
        assert isinstance(k, str)

    # Verify probabilities are sorted descending
    values = list(probs.values())
    assert values == sorted(values, reverse=True)
    assert sum(values) == pytest.approx(1.0, rel=1e-2)


def test_classifier_syntax_error_defers_to_s1(classifier: MisconceptionClassifier) -> None:
    """Code with broken syntax returns 1.0 probability on S1 meta-class."""
    broken_code = "def oops(x\n    return x"
    probs = classifier.predict_probabilities(broken_code)

    assert probs == {"S1": 1.0}


def test_classifier_predict_top(classifier: MisconceptionClassifier) -> None:
    """Verify predict_top thresholding behavior."""
    code = "def spin():\n    while True:\n        pass"
    top = classifier.predict_top(code, min_confidence=0.01)

    assert top is not None
    code_name, prob = top
    assert isinstance(code_name, str)
    assert prob > 0.01

    # High threshold should return None if not met
    high_threshold = classifier.predict_top(code, min_confidence=0.99)
    assert high_threshold is None
