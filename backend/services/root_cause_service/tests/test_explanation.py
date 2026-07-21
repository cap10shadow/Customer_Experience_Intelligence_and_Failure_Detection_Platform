from backend.services.root_cause_service.app.domain.evidence import Evidence, EvidenceType
from backend.services.root_cause_service.app.services.explanation import build_explanation, build_unknown_explanation
from backend.services.root_cause_service.app.services.rule_engine import RuleResult
from backend.shared.constants.enums.root_cause import RootCause


def test_build_explanation_includes_cause_score_band_and_reasons():
    evidence = (
        Evidence(type=EvidenceType.CATEGORY, description="Payment complaints increased", weight=40),
        Evidence(type=EvidenceType.SEVERITY, description="Incident severity is critical", weight=25),
    )
    result = RuleResult(matched=True, cause=RootCause.PAYMENT_GATEWAY_FAILURE, score=65, evidence=evidence, rule_version="1.0")

    explanation = build_explanation(result, evidence, "Medium")

    assert "payment_gateway_failure" in explanation
    assert "65" in explanation
    assert "Medium" in explanation
    assert "Payment complaints increased" in explanation
    assert "Incident severity is critical" in explanation


def test_build_explanation_with_no_evidence():
    result = RuleResult(matched=False, cause=RootCause.UNKNOWN, score=0, evidence=(), rule_version="1.0")
    explanation = build_explanation(result, (), "Weak")
    assert "No deterministic rule matched" in explanation
    assert "Weak" in explanation


def test_build_unknown_explanation():
    explanation = build_unknown_explanation()
    assert "unknown" in explanation.lower()
