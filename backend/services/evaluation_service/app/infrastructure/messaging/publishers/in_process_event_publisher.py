import logging

from backend.services.evaluation_service.app.application.dto.evaluation_completed_event import (
    EvaluationCompletedEvent,
)
from backend.services.evaluation_service.app.application.ports.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class InProcessEventPublisher(EventPublisher):
    """
    In-Process Event Publisher

    Layer:
    Infrastructure.

    Operational Purpose:
    The current, broker-less implementation of the `EventPublisher` port:
    "publishing" an outbound `EvaluationCompleted` event means recording it
    through the standard logger, since no message broker exists anywhere
    in this repository yet (no RabbitMQ/Kafka/Redis, no client library, no
    shared event-schema module -- confirmed by inspection before this Step
    was implemented). Introducing a real broker later is a pure
    Infrastructure-layer change: a new class implementing this same
    `EventPublisher` port, wired in at the same composition root
    (`presentation/dependencies.py`) -- `EvaluationLifecycleService` and
    everything above it does not change.
    """

    async def publish(self, event: EvaluationCompletedEvent) -> None:
        logger.info(
            "EvaluationCompleted published: event_id=%s caused_by_event_id=%s evaluation_id=%s "
            "incident_id=%s quality_rating=%s explainability_rating=%s occurred_at=%s",
            event.event_id,
            event.caused_by_event_id,
            event.evaluation_id,
            event.incident_id,
            event.quality_rating,
            event.explainability_rating,
            event.occurred_at,
        )
