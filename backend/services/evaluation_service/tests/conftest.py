import pytest

from backend.services.evaluation_service.app.application.completed_intelligence import CompletedIntelligence
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext
from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
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


def _make_evaluation(**overrides) -> Evaluation:
    """Builds a complete, real Evaluation by running the actual (frozen) Step 1 domain pipeline
    -- ValidationEngine -> QualityEngine/ExplainabilityEngine -> ConfidenceAnalyzer -> EvaluationBuilder
    -- against a DomainEvaluationContext. For infrastructure/presentation tests that need a real,
    non-fabricated Evaluation to persist or serialize, never a hand-built one."""
    context = _make_domain_evaluation_context(**overrides)

    validation_summary = ValidationEngine().validate(context)
    quality_assessment = QualityEngine().evaluate(context)
    explainability_assessment = ExplainabilityEngine().evaluate(context)
    confidence_summary = ConfidenceAnalyzer().summarize(context)

    return EvaluationBuilder().build(
        incident_id=context.incident_id,
        validation_summary=validation_summary,
        quality_assessment=quality_assessment,
        explainability_assessment=explainability_assessment,
        confidence_summary=confidence_summary,
    )


@pytest.fixture
def make_completed_intelligence():
    return _make_completed_intelligence


@pytest.fixture
def make_domain_evaluation_context():
    return _make_domain_evaluation_context


@pytest.fixture
def make_evaluation():
    return _make_evaluation


@pytest.fixture
def anyio_backend():
    return "asyncio"
