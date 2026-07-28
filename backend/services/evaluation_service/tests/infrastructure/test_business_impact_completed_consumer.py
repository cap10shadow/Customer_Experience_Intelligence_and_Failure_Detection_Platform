"""
Unit tests for BusinessImpactCompletedConsumer: deserialization,
translation, and delegation only -- no validation, no repository access,
no Evaluation computation of its own (verified by asserting the fake
lifecycle service is never invoked for a malformed payload).
"""

import uuid

import pytest

from backend.services.evaluation_service.app.application.dto.evaluation_execution_request import (
    EvaluationExecutionRequest,
)
from backend.services.evaluation_service.app.application.lifecycle.evaluation_execution_result import (
    EvaluationExecutionResult,
    ExecutionOutcome,
)
from backend.services.evaluation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
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

    async def execute(self, request: EvaluationExecutionRequest) -> EvaluationExecutionResult:
        self.received_requests.append(request)
        if self._exception is not None:
            raise self._exception
        return self._result


def _valid_raw_payload(**overrides) -> dict:
    payload = {
        "event_id": str(uuid.uuid4()),
        "incident_id": "INC-EVENT-0001",
        "root_cause": "service_outage",
        "root_cause_confidence_score": 85,
        "root_cause_explanation": "service_outage identified with critical anomaly severity",
        "root_cause_evidence_count": 2,
        "root_cause_id": str(uuid.uuid4()),
        "business_impact_overall_score": 75,
        "business_impact_overall_severity": "high",
        "business_impact_business_priority": "high",
        "business_impact_confidence": 80,
        "business_impact_explanation": (
            "Overall business impact is high (score: 75, priority: high). "
            "Reasons: financial (critical): incident severity is critical."
        ),
        "assessment_id": str(uuid.uuid4()),
    }
    payload.update(overrides)
    return payload


@pytest.mark.anyio
async def test_successful_message_processing_translates_and_delegates():
    expected = EvaluationExecutionResult(outcome=ExecutionOutcome.COMPLETED, evaluation_id=uuid.uuid4())
    lifecycle_service = _FakeLifecycleService(result=expected)
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload()

    result = await consumer.consume(raw_payload)

    assert result is expected
    assert len(lifecycle_service.received_requests) == 1
    request = lifecycle_service.received_requests[0]
    assert str(request.event_id) == raw_payload["event_id"]
    assert str(request.root_cause_id) == raw_payload["root_cause_id"]
    assert str(request.assessment_id) == raw_payload["assessment_id"]
    assert request.completed_intelligence.incident_id == raw_payload["incident_id"]
    assert request.completed_intelligence.root_cause.value == raw_payload["root_cause"]


@pytest.mark.anyio
async def test_malformed_payload_is_rejected_without_invoking_the_lifecycle_service():
    lifecycle_service = _FakeLifecycleService(
        result=EvaluationExecutionResult(outcome=ExecutionOutcome.COMPLETED, evaluation_id=uuid.uuid4())
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload()
    del raw_payload["incident_id"]  # missing required field

    result = await consumer.consume(raw_payload)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert lifecycle_service.received_requests == []


@pytest.mark.anyio
async def test_malformed_payload_with_invalid_root_cause_is_rejected():
    lifecycle_service = _FakeLifecycleService(
        result=EvaluationExecutionResult(outcome=ExecutionOutcome.COMPLETED, evaluation_id=uuid.uuid4())
    )
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)
    raw_payload = _valid_raw_payload(root_cause="not_a_real_root_cause")

    result = await consumer.consume(raw_payload)

    assert result.outcome == ExecutionOutcome.REJECTED
    assert lifecycle_service.received_requests == []


@pytest.mark.anyio
async def test_retryable_infrastructure_exception_propagates_uncaught():
    lifecycle_service = _FakeLifecycleService(exception=ConnectionError("simulated: database unreachable"))
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)

    with pytest.raises(ConnectionError, match="simulated: database unreachable"):
        await consumer.consume(_valid_raw_payload())


@pytest.mark.anyio
async def test_deterministic_business_rejection_is_returned_normally():
    expected = EvaluationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason="Duplicate event")
    lifecycle_service = _FakeLifecycleService(result=expected)
    consumer = BusinessImpactCompletedConsumer(lifecycle_service)

    result = await consumer.consume(_valid_raw_payload())

    assert result is expected
    assert len(lifecycle_service.received_requests) == 1
