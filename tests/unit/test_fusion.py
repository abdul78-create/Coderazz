"""Unit tests for the Multi-Source Misconception Fusion Engine."""

from unittest.mock import AsyncMock

import pytest

from backend.app.models.misconception import DetectorType
from backend.app.models.submission import SubmissionVerdict
from backend.app.services.sandbox import SandboxExecutionResult, SandboxService
from ml.classifier import MisconceptionClassifier
from ml.fusion import FusedDiagnosis, MisconceptionFusionEngine


@pytest.fixture(scope="module")
def fusion_engine() -> MisconceptionFusionEngine:
    """Shared fusion engine with initialized classifier."""
    return MisconceptionFusionEngine()


@pytest.mark.asyncio
async def test_fusion_tier_1_syntax_error(fusion_engine: MisconceptionFusionEngine) -> None:
    """Broken syntax must immediately yield S1 with confidence 1.0."""
    code = "def broken(x\n    return x"
    res: FusedDiagnosis = await fusion_engine.diagnose(code)

    assert res.misconception_code == "S1"
    assert res.confidence == 1.0
    assert res.detector_type == DetectorType.RULE_AST
    assert 1 in res.evidence_lines
    assert "Syntax error" in res.explanation


@pytest.mark.asyncio
async def test_fusion_tier_2_deterministic_rule(fusion_engine: MisconceptionFusionEngine) -> None:
    """High-confidence deterministic AST rule takes precedence over ML and prober."""
    code = "def off_by_one(arr):\n    for i in range(len(arr) + 1):\n        print(arr[i])"
    res: FusedDiagnosis = await fusion_engine.diagnose(code)

    assert res.misconception_code == "A1"
    assert res.confidence >= 0.90
    assert res.detector_type == DetectorType.RULE_AST
    assert 2 in res.evidence_lines
    assert "off-by-one" in res.explanation.lower()


@pytest.mark.asyncio
async def test_fusion_tier_3_prober_precedence(fusion_engine: MisconceptionFusionEngine) -> None:
    """When deterministic rules do not trigger, sandbox boundary probes take precedence."""
    # Code that doesn't trigger our 10 rules directly, but crashes on probe
    code = "def lookup(x):\n    d = {'a': 1}\n    return d[x]"

    mock_sandbox = AsyncMock(spec=SandboxService)
    # Simulate KeyError on empty input probe
    mock_sandbox.execute_code_once.return_value = SandboxExecutionResult(
        stdout="",
        stderr="Traceback (most recent call last):\n  File 'sol.py', line 3, in lookup\nKeyError: ''\n",
        exit_code=1,
        runtime_ms=25,
        memory_kb=1024,
        verdict=SubmissionVerdict.RUNTIME_ERROR,
    )

    res: FusedDiagnosis = await fusion_engine.diagnose(code, sandbox=mock_sandbox)

    assert res.misconception_code == "E2"
    assert res.confidence >= 0.90
    assert res.detector_type == DetectorType.PROBE
    assert "KeyError" in res.explanation


@pytest.mark.asyncio
async def test_fusion_tier_4_ml_classifier() -> None:
    """When rules and probes do not trigger, ML classifier fires if top prob >= 0.40."""
    mock_classifier = MisconceptionClassifier()
    # Mock predict_probabilities to return > 0.40 on a code snippet
    mock_classifier.predict_probabilities = lambda _: {"A4": 0.65, "A1": 0.20, "D4": 0.15}  # type: ignore

    engine = MisconceptionFusionEngine(classifier=mock_classifier)
    code = "def sample(x):\n    # some ambiguous structure\n    return x"
    res: FusedDiagnosis = await engine.diagnose(code, sandbox=None)

    assert res.misconception_code == "A4"
    assert res.confidence == 0.65
    assert res.detector_type == DetectorType.ML_CLASSIFIER
    assert len(res.secondary_candidates) >= 2


@pytest.mark.asyncio
async def test_fusion_tier_5_novel_fallback() -> None:
    """When rules do not fire and ML confidence is below 0.40, fallback to S2."""
    mock_classifier = MisconceptionClassifier()
    # Mock low confidence across all classes
    mock_classifier.predict_probabilities = lambda _: {"A1": 0.15, "B1": 0.12, "C1": 0.10}  # type: ignore

    engine = MisconceptionFusionEngine(classifier=mock_classifier)
    code = "def obscure(data):\n    return data"
    res: FusedDiagnosis = await engine.diagnose(code, sandbox=None)

    assert res.misconception_code == "S2"
    assert res.confidence == 0.30
    assert res.detector_type == DetectorType.FUSION
    assert "S2 (Novel / Unclassified Misconception)" in res.explanation
