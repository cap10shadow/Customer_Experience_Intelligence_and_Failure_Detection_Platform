import pytest

from backend.services.evaluation_service.app.application.completed_intelligence import CompletedIntelligence
from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext
from backend.shared.constants.enums.root_cause import RootCause


def _make_completed_intelligence(
    *,
    incident_id="INC-TEST0001",
    root_cause=RootCause.SERVICE_OUTAGE,
    root_cause_confidence_score=85,
    root_cause_explanation="service_outage identified with critical anomaly severity",
    root_cause_evidence_count=2,
    business_impact_overall_score=75,
    business_impact_overall_severity="high",
    business_impact_business_priority="high",
    business_impact_confidence=80,
    business_impact_explanation=(
        "Overall business impact is high (score: 75, priority: high). "
        "Reasons: financial (critical): incident severity is critical."
    ),
) -> CompletedIntelligence:
    """Builds a plain, in-memory CompletedIntelligence for orchestrator/mapper unit tests."""
    return CompletedIntelligence(
        incident_id=incident_id,
        root_cause=root_cause,
        root_cause_confidence_score=root_cause_confidence_score,
        root_cause_explanation=root_cause_explanation,
        root_cause_evidence_count=root_cause_evidence_count,
        business_impact_overall_score=business_impact_overall_score,
        business_impact_overall_severity=business_impact_overall_severity,
        business_impact_business_priority=business_impact_business_priority,
        business_impact_confidence=business_impact_confidence,
        business_impact_explanation=business_impact_explanation,
    )


def _make_domain_evaluation_context(
    *,
    incident_id="INC-TEST0001",
    root_cause=RootCause.SERVICE_OUTAGE,
    root_cause_confidence_score=85,
    root_cause_explanation="service_outage identified with critical anomaly severity",
    root_cause_evidence_count=2,
    business_impact_overall_score=75,
    business_impact_overall_severity="high",
    business_impact_business_priority="high",
    business_impact_confidence=80,
    business_impact_explanation=(
        "Overall business impact is high (score: 75, priority: high). "
        "Reasons: financial (critical): incident severity is critical."
    ),
) -> DomainEvaluationContext:
    """Builds a plain, in-memory DomainEvaluationContext for engine unit tests (ValidationEngine,
    QualityEngine, ExplainabilityEngine, ConfidenceAnalyzer -- the Domain-layer components that must
    never depend on the Application layer's CompletedIntelligence DTO)."""
    return DomainEvaluationContext(
        incident_id=incident_id,
        root_cause=root_cause,
        root_cause_confidence_score=root_cause_confidence_score,
        root_cause_explanation=root_cause_explanation,
        root_cause_evidence_count=root_cause_evidence_count,
        business_impact_overall_score=business_impact_overall_score,
        business_impact_overall_severity=business_impact_overall_severity,
        business_impact_business_priority=business_impact_business_priority,
        business_impact_confidence=business_impact_confidence,
        business_impact_explanation=business_impact_explanation,
    )


@pytest.fixture
def make_completed_intelligence():
    return _make_completed_intelligence


@pytest.fixture
def make_domain_evaluation_context():
    return _make_domain_evaluation_context


@pytest.fixture
def anyio_backend():
    return "asyncio"
