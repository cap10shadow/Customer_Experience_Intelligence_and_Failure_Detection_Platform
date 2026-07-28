from typing import Any, Dict

from backend.services.evaluation_service.app.application.completed_intelligence import CompletedIntelligence
from backend.services.evaluation_service.app.application.dto.evaluation_execution_request import (
    EvaluationExecutionRequest,
)
from backend.services.evaluation_service.app.application.lifecycle.evaluation_execution_result import (
    EvaluationExecutionResult,
    ExecutionOutcome,
)
from backend.services.evaluation_service.app.application.lifecycle.evaluation_lifecycle_service import (
    EvaluationLifecycleService,
)
from backend.services.evaluation_service.app.infrastructure.messaging.consumers.business_impact_completed_payload import (
    BusinessImpactCompletedPayload,
    MalformedPayloadError,
)


class BusinessImpactCompletedConsumer:
    """
    BusinessImpactCompleted Event Consumer

    Layer:
    Infrastructure.

    Operational Purpose:
    Receives one raw `BusinessImpactCompleted` transport payload, deserializes
    it, translates it into the Application-owned `EvaluationExecutionRequest`,
    and invokes `EvaluationLifecycleService`. This is the entire
    responsibility of this class -- nothing else.

    Transport note: no message broker exists anywhere in this repository
    today (confirmed by inspection -- no RabbitMQ/Kafka/Redis, no client
    library, no shared event-schema module). This consumer is therefore
    exposed in-process, behind a thin Presentation-layer HTTP route
    (`presentation/api/internal_events.py`) that does nothing but hand this
    class's `consume()` the deserialized JSON request body. Wiring a real
    broker later means writing a new adapter that calls this same
    `consume()` from its own message callback -- this class does not
    change.

    Must NOT (and does not):
    - perform validation of any kind (structural or business) beyond what
      is required to deserialize the payload itself;
    - execute business rules;
    - access any repository directly;
    - compute an Evaluation.

    Failure classification:
    - A malformed payload is caught here and returned as a normal REJECTED
      result -- `EvaluationLifecycleService` is never invoked, since there
      is nothing valid to invoke it with.
    - Anything `EvaluationLifecycleService.execute()` itself raises (rather
      than returns) is a transient infrastructure condition by definition
      (see that method's own docstring) and is deliberately left
      unguarded here, propagating to whatever hosts this consumer. A real
      broker integration would retry such a message per its own policy;
      the deterministic REJECTED/FAILED outcomes returned (not raised) by
      `execute()` must never be retried the same way -- retrying a
      duplicate-event rejection or a validation failure changes nothing.
    """

    def __init__(self, lifecycle_service: EvaluationLifecycleService) -> None:
        self._lifecycle_service = lifecycle_service

    async def consume(self, raw_payload: Dict[str, Any]) -> EvaluationExecutionResult:
        try:
            payload = BusinessImpactCompletedPayload.from_raw(raw_payload)
        except MalformedPayloadError as exc:
            return EvaluationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason=str(exc))

        request = EvaluationExecutionRequest(
            event_id=payload.event_id,
            root_cause_id=payload.root_cause_id,
            assessment_id=payload.assessment_id,
            completed_intelligence=CompletedIntelligence(
                incident_id=payload.incident_id,
                root_cause=payload.root_cause,
                root_cause_confidence_score=payload.root_cause_confidence_score,
                root_cause_explanation=payload.root_cause_explanation,
                root_cause_evidence_count=payload.root_cause_evidence_count,
                business_impact_overall_score=payload.business_impact_overall_score,
                business_impact_overall_severity=payload.business_impact_overall_severity,
                business_impact_business_priority=payload.business_impact_business_priority,
                business_impact_confidence=payload.business_impact_confidence,
                business_impact_explanation=payload.business_impact_explanation,
            ),
        )

        return await self._lifecycle_service.execute(request)
