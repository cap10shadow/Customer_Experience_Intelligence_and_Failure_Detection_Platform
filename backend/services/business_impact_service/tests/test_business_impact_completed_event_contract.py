"""
Contract tests (Part 6): prove `BusinessImpactEventPublisher`'s two
generated payloads are genuinely valid input to recommendation_service's
and evaluation_service's own, already-frozen `BusinessImpactCompletedPayload.
from_raw()` parsers -- imported directly, no HTTP, no mocking of the
consumer side. This is the regression guard against the publisher ever
drifting out of sync with either consumer's real (and structurally
different, per Part 6's research) schema.
"""

import uuid

import pytest

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.services.business_impact_service.app.services.business_impact_event_publisher import (
    BusinessImpactCompletedEvent,
    build_evaluation_payload,
    build_recommendation_payload,
)
from backend.services.evaluation_service.app.infrastructure.messaging.consumers.business_impact_completed_payload import (
    BusinessImpactCompletedPayload as EvaluationPayload,
)
from backend.services.recommendation_service.app.infrastructure.messaging.consumers.business_impact_completed_payload import (
    BusinessImpactCompletedPayload as RecommendationPayload,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.business_impact_assessment import BusinessImpactAssessmentStatus
from backend.shared.constants.enums.root_cause import RootCause


def _event() -> BusinessImpactCompletedEvent:
    incident_id = uuid.uuid4()
    assessment = BusinessImpactAssessmentEntity(
        assessment_id=uuid.uuid4(),
        incident_id=incident_id,
        root_cause_id=uuid.uuid4(),
        financial=ImpactLevel.CRITICAL,
        customer=ImpactLevel.CRITICAL,
        operational=ImpactLevel.CRITICAL,
        sla=ImpactLevel.NONE,
        reputation=ImpactLevel.NONE,
        overall_score=75,
        overall_severity=ImpactLevel.HIGH,
        business_priority=BusinessPriority.HIGH,
        confidence=60,
        estimated_affected_customers=500,
        explanation="Overall business impact is high (score: 75, priority: high).",
        status=BusinessImpactAssessmentStatus.ACTIVE,
    )
    root_cause = PersistedRootCause(
        id=uuid.uuid4(),
        incident_id=incident_id,
        cause=RootCause.SERVICE_OUTAGE,
        confidence_score=90,
        confidence_level="Very High",
        evidence=[{"source": "anomaly_detection", "description": "spike", "weight": 5}],
        explanation="service_outage identified with critical anomaly severity",
    )
    return BusinessImpactCompletedEvent(
        event_id=uuid.uuid4(),
        incident_id=incident_id,
        incident_severity=AnomalySeverity.CRITICAL,
        assessment=assessment,
        root_cause=root_cause,
    )


def test_recommendation_payload_is_valid_input_to_the_real_recommendation_consumer():
    event = _event()
    raw = build_recommendation_payload(event)

    parsed = RecommendationPayload.from_raw(raw)

    assert parsed.event_id == event.event_id
    assert parsed.intelligence_context.incident.incident_id == str(event.incident_id)
    assert parsed.intelligence_context.incident.severity == AnomalySeverity.CRITICAL
    assert parsed.intelligence_context.business_impact.business_score == 75
    assert parsed.intelligence_context.root_cause is not None
    assert parsed.intelligence_context.root_cause.cause == RootCause.SERVICE_OUTAGE
    # Legitimately omitted, not fabricated -- both Optional on the real schema.
    assert parsed.intelligence_context.nlp_intelligence is None
    assert parsed.intelligence_context.anomaly_intelligence is None


def test_evaluation_payload_is_valid_input_to_the_real_evaluation_consumer():
    event = _event()
    raw = build_evaluation_payload(event)

    parsed = EvaluationPayload.from_raw(raw)

    assert parsed.event_id == event.event_id
    assert parsed.incident_id == str(event.incident_id)
    assert parsed.root_cause == RootCause.SERVICE_OUTAGE
    assert parsed.root_cause_confidence_score == 90
    assert parsed.root_cause_explanation == "service_outage identified with critical anomaly severity"
    assert parsed.root_cause_evidence_count == 1
    assert parsed.root_cause_id == event.root_cause.id
    assert parsed.business_impact_overall_score == 75
    assert parsed.business_impact_explanation.startswith("Overall business impact is high")
    assert parsed.assessment_id == event.assessment.assessment_id


def test_both_parsed_payloads_carry_the_identical_event_id():
    event = _event()

    recommendation_parsed = RecommendationPayload.from_raw(build_recommendation_payload(event))
    evaluation_parsed = EvaluationPayload.from_raw(build_evaluation_payload(event))

    assert recommendation_parsed.event_id == evaluation_parsed.event_id == event.event_id


def test_root_cause_with_no_evidence_still_parses_with_a_zero_count():
    event = _event()
    object.__setattr__(event.root_cause, "evidence", [])

    parsed = EvaluationPayload.from_raw(build_evaluation_payload(event))

    assert parsed.root_cause_evidence_count == 0


@pytest.fixture
def anyio_backend():
    return "asyncio"
