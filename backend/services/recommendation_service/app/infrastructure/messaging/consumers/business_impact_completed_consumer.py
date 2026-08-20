from typing import Any, Dict

from backend.services.recommendation_service.app.application.dto.recommendation_execution_request import (
    RecommendationExecutionRequest,
)
from backend.services.recommendation_service.app.application.lifecycle.recommendation_execution_result import (
    ExecutionOutcome,
    RecommendationExecutionResult,
)
from backend.services.recommendation_service.app.application.lifecycle.recommendation_lifecycle_service import (
    RecommendationLifecycleService,
)
from backend.services.recommendation_service.app.infrastructure.messaging.consumers.business_impact_completed_payload import (
    BusinessImpactCompletedPayload,
    MalformedPayloadError,
)


class BusinessImpactCompletedConsumer:
    """
    BusinessImpactCompleted Event Consumer

    Layer:
    Infrastructure.

    Operational Purpose:
    Receives one raw `BusinessImpactCompleted` transport payload,
    deserializes and validates its transport schema, translates it into
    the Application-owned `RecommendationExecutionRequest`, and invokes
    `RecommendationLifecycleService`. This is the entire responsibility of
    this class -- nothing else.

    Transport note: no message broker exists anywhere in this repository
    (confirmed by `evaluation_service`'s own Step 3 architecture
    assessment, still true here). This consumer is therefore exposed
    in-process, behind a thin Presentation-layer HTTP route
    (`presentation/api/internal_events.py`) that does nothing but hand
    this class's `consume()` the deserialized JSON request body. Wiring a
    real broker later means writing a new adapter that calls this same
    `consume()` from its own message callback -- this class does not
    change.

    Must NOT (and does not):
    - execute Recommendation Rules;
    - access any repository directly;
    - perform lifecycle validation (structural payload validation is not
      the same thing -- see below);
    - publish outbound events.

    Failure classification:
    - A malformed payload (missing required fields, unparseable enum
      values, etc.) is caught here and returned as a normal REJECTED
      result -- `RecommendationLifecycleService` is never invoked, since
      there is nothing valid to invoke it with.
    - Anything `RecommendationLifecycleService.execute()` itself raises
      (rather than returns) is a transient infrastructure condition by
      definition (see that method's own docstring) and is deliberately
      left unguarded here, propagating to whatever hosts this consumer. A
      real broker integration would retry such a message per its own
      policy; the deterministic REJECTED/FAILED outcomes returned (not
      raised) by `execute()` must never be retried the same way --
      retrying a duplicate-event rejection or a validation failure
      changes nothing, and should route to a Dead Letter Queue or simply
      be acknowledged as rejected, per the frozen Messaging Behaviour.
    """

    def __init__(self, lifecycle_service: RecommendationLifecycleService) -> None:
        self._lifecycle_service = lifecycle_service

    async def consume(self, raw_payload: Dict[str, Any]) -> RecommendationExecutionResult:
        try:
            payload = BusinessImpactCompletedPayload.from_raw(raw_payload)
        except MalformedPayloadError as exc:
            return RecommendationExecutionResult(outcome=ExecutionOutcome.REJECTED, reason=str(exc))

        request = RecommendationExecutionRequest(
            event_id=payload.event_id,
            dataset_id=payload.dataset_id,
            dataset_version_id=payload.dataset_version_id,
            intelligence_context=payload.intelligence_context,
        )

        return await self._lifecycle_service.execute(request)
