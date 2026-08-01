import logging

from backend.services.recommendation_service.app.application.dto.recommendations_generated_event import (
    RecommendationsGeneratedEvent,
)
from backend.services.recommendation_service.app.application.ports.recommendation_event_publisher import (
    RecommendationEventPublisher,
)

logger = logging.getLogger(__name__)


class InProcessRecommendationEventPublisher(RecommendationEventPublisher):
    """
    In-Process Recommendation Event Publisher

    Layer:
    Infrastructure.

    Operational Purpose:
    The current, broker-less implementation of the
    `RecommendationEventPublisher` port: "publishing" an outbound
    `RecommendationsGenerated` event means recording it through the
    standard logger, since no message broker exists anywhere in this
    repository yet -- the same accepted prototype-stage tradeoff
    `evaluation_service`'s `InProcessEventPublisher` already established.
    Introducing a real broker later is a pure Infrastructure-layer change:
    a new class implementing this same `RecommendationEventPublisher`
    port, wired in at the same composition root
    (`presentation/dependencies.py`) -- `RecommendationLifecycleService`
    and everything above it does not change.
    """

    async def publish(self, event: RecommendationsGeneratedEvent) -> None:
        logger.info(
            "RecommendationsGenerated published: generation_id=%s incident_id=%s recommendation_count=%s "
            "highest_priority=%s created_at=%s",
            event.generation_id,
            event.incident_id,
            event.recommendation_count,
            event.highest_priority,
            event.created_at,
        )
