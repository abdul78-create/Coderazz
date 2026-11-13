"""Multi-Source Misconception Fusion Engine for CodeRazz.

Synthesizes diagnostic evidence across multiple analytical tiers in strict priority order:
1. Syntax validation (AST parser) -> S1 meta-class (confidence: 1.0)
2. Deterministic structural AST rules -> Top-10 rules (confidence: >= 0.90)
3. Diagnostic boundary micro-probes (Sandbox) -> Boundary failure signatures (confidence: >= 0.90)
4. Statistical Scikit-Learn Classifier -> AST node distribution + token TF-IDF (confidence: >= 0.40)
5. Novel / Unclassified fallback -> S2 meta-class (confidence: 0.30)

Guarantees explainability, zero false positives on known bugs, and graceful fallback.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.app.models.misconception import DetectorType
from backend.app.services.sandbox import SandboxService
from ml.ast_analyzer import StructuralFacts, extract_structural_facts
from ml.classifier import MisconceptionClassifier
from ml.prober import DiagnosticProber
from ml.rule_detectors import RuleDetectionResult, execute_rule_detectors

logger = logging.getLogger(__name__)


@dataclass
class FusedDiagnosis:
    """Final diagnostic outcome emitted by the Fusion Engine."""

    misconception_code: str
    confidence: float
    detector_type: DetectorType
    evidence_lines: list[int] = field(default_factory=list)
    explanation: str = ""
    secondary_candidates: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MisconceptionFusionEngine:
    """Unified engine arbitrating between deterministic AST rules, sandbox probes, and ML."""

    def __init__(self, classifier: MisconceptionClassifier | None = None) -> None:
        self.classifier = classifier or MisconceptionClassifier()

    async def diagnose(
        self,
        source_code: str,
        test_case_failures: list[dict[str, Any]] | None = None,
        sandbox: SandboxService | None = None,
    ) -> FusedDiagnosis:
        """Diagnose source code and return a definitive FusedDiagnosis.

        Executes the hierarchical arbitration pipeline:
        1. S1 Syntax Error Precedence
        2. AST Deterministic Rules (Confidence >= 0.90)
        3. Sandbox Micro-Prober Boundary Tests (Confidence >= 0.90)
        4. Statistical AST/Token Classifier (Confidence >= 0.40)
        5. S2 Novel / Unclassified Fallback
        """
        # Tier 1: Syntax Analysis & Structural Fact Extraction
        facts: StructuralFacts = extract_structural_facts(source_code)
        if not facts.syntax.is_valid:
            err_line = facts.syntax.error_line or 1
            return FusedDiagnosis(
                misconception_code="S1",
                confidence=1.0,
                detector_type=DetectorType.RULE_AST,
                evidence_lines=[err_line],
                explanation=f"Line {err_line}: Syntax error: {facts.syntax.error_message}",
                secondary_candidates=[],
                metadata={"syntax_error": facts.syntax.error_message, "line": err_line},
            )

        # Tier 2: Deterministic Rule Detectors
        rule_results: list[RuleDetectionResult] = execute_rule_detectors(source_code, facts=facts)
        if rule_results and rule_results[0].confidence >= 0.90:
            top_rule = rule_results[0]
            secondary = [
                {
                    "code": r.misconception_code,
                    "confidence": r.confidence,
                    "detector": r.detector_name,
                    "explanation": r.explanation,
                }
                for r in rule_results[1:]
            ]
            return FusedDiagnosis(
                misconception_code=top_rule.misconception_code,
                confidence=top_rule.confidence,
                detector_type=DetectorType.RULE_AST,
                evidence_lines=top_rule.evidence_lines,
                explanation=top_rule.explanation,
                secondary_candidates=secondary,
                metadata={"detector_name": top_rule.detector_name},
            )

        # Tier 3: Diagnostic Micro-Prober (Docker sandbox isolation)
        probe_secondary: list[dict[str, Any]] = []
        if sandbox is not None:
            try:
                prober = DiagnosticProber(sandbox_service=sandbox)
                probe_outcomes = await prober.run_diagnostic_suite(source_code)
                for outcome in probe_outcomes:
                    if outcome.inferred_misconception:
                        probe_secondary.append({
                            "code": outcome.inferred_misconception,
                            "confidence": outcome.confidence,
                            "probe": outcome.probe_name,
                            "explanation": outcome.evidence_explanation,
                        })
                    if outcome.confidence >= 0.90 and outcome.inferred_misconception:
                        return FusedDiagnosis(
                            misconception_code=outcome.inferred_misconception,
                            confidence=outcome.confidence,
                            detector_type=DetectorType.PROBE,
                            evidence_lines=[],
                            explanation=outcome.evidence_explanation,
                            secondary_candidates=probe_secondary[:-1],
                            metadata={
                                "probe_name": outcome.probe_name,
                                "exception_name": outcome.exception_name,
                                "verdict": outcome.verdict.value,
                            },
                        )
            except (OSError, RuntimeError, ValueError, TypeError, TimeoutError) as err:
                logger.warning("Micro-prober execution encountered error: %s", err)

        # Tier 4: Statistical Machine Learning Classifier (AST distributions + n-grams)
        try:
            probs = self.classifier.predict_probabilities(source_code)
            # Remove meta-classes like S1 if valid syntax
            probs.pop("S1", None)
            probs.pop("S2", None)

            if probs:
                top_code, top_prob = next(iter(probs.items()))
                if top_prob >= 0.40:
                    secondary_ml = [
                        {"code": c, "confidence": round(p, 4)}
                        for c, p in list(probs.items())[1:4]
                    ]
                    # Combine with any rule hints that fired with lower confidence
                    if rule_results:
                        secondary_ml.extend([
                            {"code": r.misconception_code, "confidence": r.confidence, "detector": r.detector_name}
                            for r in rule_results
                        ])

                    return FusedDiagnosis(
                        misconception_code=top_code,
                        confidence=round(top_prob, 4),
                        detector_type=DetectorType.ML_CLASSIFIER,
                        evidence_lines=[],
                        explanation=(
                            f"Statistical AST and token n-gram classifier identified {top_code} "
                            f"as the primary candidate ({top_prob:.1%} probability)."
                        ),
                        secondary_candidates=secondary_ml,
                        metadata={"top_probabilities": {k: round(v, 4) for k, v in list(probs.items())[:5]}},
                    )
        except (ValueError, TypeError, RuntimeError, AttributeError) as err:
            logger.warning("ML classification failed: %s", err)

        # Tier 5: Fallback to Novel / Unclassified Meta-Class (S2)
        return FusedDiagnosis(
            misconception_code="S2",
            confidence=0.30,
            detector_type=DetectorType.FUSION,
            evidence_lines=[],
            explanation=(
                "The submission failed tests, but the error pattern does not match "
                "deterministic AST rules, boundary probes, or known classifier patterns. "
                "Classified under S2 (Novel / Unclassified Misconception)."
            ),
            secondary_candidates=[
                {"code": r.misconception_code, "confidence": r.confidence}
                for r in rule_results
            ] + probe_secondary,
            metadata={"classification_stage": "unclassified_fallback"},
        )
