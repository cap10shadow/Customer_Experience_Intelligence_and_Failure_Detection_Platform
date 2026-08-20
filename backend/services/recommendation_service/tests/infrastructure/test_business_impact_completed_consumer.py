"""
Unit tests for BusinessImpactCompletedConsumer: deserialization,
translation, and delegation only -- no lifecycle validation, no repository
access, no Recommendation Rule execution of its own (verified by asserting
the fake lifecycle service is never invoked for a malformed payload).
"""

import uuid

import pytest

from backend.services.recommendation_service.app.application.dto.recommendation_execution_request import (
    RecommendationExecutionRequest,
)
from backend.services.recommendation_service.app.application.lifecycle.recommendation_execution_result import (
    ExecutionOutcome,
    RecommendationExecutionResult,
)
from backend.services.recommendation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeLifecycleService:
    def __init__(self, result=None, exception=None):
        self._result = result
        self._exception = exception
        self.received_requests: list = []

    async def execute(self, request: RecommendationExecutionRequest) -> RecommendationExecutionResult:
        self.received_requests.append(request)
        if self._exception is not None:
            raise self._exception
        return self._result


def _valid_raw_payload(**overrides) -> dict:
    payload = {
        "event_id": str(uuid.uuid4()),
        "dataset_id": str(uuid.uuid4()),
        "dataset_version_id": str(uuid.uuid4()),
        "incident": {
            "incident_id": "INC-EVENT-0001",
            "severity": "critical",
            "categories": ["operational_failure"],
            "regions": ["us-east"],
            "urgency_levels": ["high"],
        },
        "business_impact": {
            "business_score": 90,
            "overall_severity": "critical",
            "business_priority": "critical",
            "confidence": 80,
            "financial_impact": "critical",
            "customer_impact": "high",
            "operational_impact": "medium",
            "sla_impact": "high",
            "reputation_impact": "medium",
        },
        "root_cause": {
            "cause": "service_outage",
            "confidence_score": 85,
            "confidence_level": "High",
        },
        "nlp_intelligence": None,
        "anomaly_intelligence": None,
    }
    payload.update(overrides)
    return payload


@pytest.mark.anyio
async def test_successful_message_processing_translates_and_delegates():
    expected = RecommendationExecutionResult(outcome=ExecutionOutcome.COMPLETED, generation_id=uuid.uuid4(), recommendation_count=3)
    lifecycle_service = _FakeLifecycleService(result=expected)
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload()

    result = await consumer.consume(raw_payload)

    assert result is expected
    assert len(lifecycle_service.received_requests) == 1
    request = lifecycle_service.received_requests[0]
    assert str(request.event_id) == raw_payload["event_id"]
    assert request.intelligence_context.incident.incident_id == "INC-EVENT-0001"
    assert request.intelligence_context.business_impact.overall_severity == "critical"
    assert request.intelligence_context.root_cause.cause.value == "service_outage"


@pytest.mark.anyio
async def test_malformed_payload_is_rejected_without_invoking_the_lifecycle_service():
    lifecycle_service = _FakeLifecycleService(
        result=RecommendationExecutionResult(outcome=ExecutionOutcome.COMPLETED, generation_id=uuid.uuid4())
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload()
    del raw_payload["incident"]  # missing required field group

    result = await consumer.consume(raw_payload)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert lifecycle_service.received_requests == []


@pytest.mark.anyio
async def test_missing_required_nested_field_is_rejected():
    lifecycle_service = _FakeLifecycleService(
        result=RecommendationExecutionResult(outcome=ExecutionOutcome.COMPLETED, generation_id=uuid.uuid4())
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload()
    del raw_payload["business_impact"]["overall_severity"]

    result = await consumer.consume(raw_payload)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert lifecycle_service.received_requests == []


@pytest.mark.anyio
async def test_malformed_payload_with_invalid_severity_enum_is_rejected():
    lifecycle_service = _FakeLifecycleService(
        result=RecommendationExecutionResult(outcome=ExecutionOutcome.COMPLETED, generation_id=uuid.uuid4())
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload()
    raw_payload["incident"]["severity"] = "not_a_real_severity"

    result = await consumer.consume(raw_payload)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert lifecycle_service.received_requests == []


@pytest.mark.anyio
async def test_optional_root_cause_may_be_absent():
    expected = RecommendationExecutionResult(outcome=ExecutionOutcome.COMPLETED, generation_id=uuid.uuid4())
    lifecycle_service = _FakeLifecycleService(result=expected)
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload(root_cause=None)

    result = await consumer.consume(raw_payload)

    assert result is expected
    assert lifecycle_service.received_requests[0].intelligence_context.root_cause is None


@pytest.mark.anyio
async def test_retryable_infrastructure_exception_propagates_uncaught():
    lifecycle_service = _FakeLifecycleService(exception=ConnectionError("simulated: database unreachable"))
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)

    with pytest.raises(ConnectionError, match="simulated: database unreachable"):
        await consumer.consume(_valid_raw_payload())


@pytest.mark.anyio
async def test_deterministic_business_rejection_is_returned_normally():
    expected = RecommendationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason="Duplicate event")
    lifecycle_service = _FakeLifecycleService(result=expected)
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)

    result = await consumer.consume(_valid_raw_payload())

    assert result is expected
    assert len(lifecycle_service.received_requests) == 1


@pytest.mark.anyio
async def test_duplicate_event_result_is_returned_normally_not_raised():
    """A duplicate-event REJECTED result must never manifest as a dead-lettered exception -- it is a normal, returned outcome."""
    expected = RecommendationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason="Duplicate event: already processed")
    lifecycle_service = _FakeLifecycleService(result=expected)
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)

    result = await consumer.consume(_valid_raw_payload())

    assert result.outcome == ExecutionOutcome.REJECTED
