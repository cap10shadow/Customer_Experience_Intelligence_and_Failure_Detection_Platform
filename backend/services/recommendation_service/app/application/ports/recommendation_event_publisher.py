from abc import ABC, abstractmethod

from backend.services.recommendation_service.app.application.dto.recommendations_generated_event import (
    RecommendationsGeneratedEvent,
)


class RecommendationEventPublisher(ABC):
    """
    Recommendation Event Publisher (Application-owned port)

    Operational Purpose:
    Defines the outbound-integration-event contract
    `RecommendationLifecycleService` depends on, without depending on any
    messaging technology itself. Infrastructure implements this interface;
    publishing *decisions* (whether/when to publish) remain entirely owned
    by `RecommendationLifecycleService` -- this port only ever transmits
    what it is told to, exactly as `RecommendationRepository` only ever
    persists what it is handed. The same Dependency Inversion pattern
    `evaluation_service`'s `EventPublisher` already established.

    Architectural Boundaries:
    - `publish()` is called only after a successful commit -- never
      before, never speculatively. If it raises, the caller
      (`RecommendationLifecycleService`) logs at CRITICAL severity and
      does not retry or roll anything back: the Outbox Pattern is
      intentionally not implemented (accepted prototype-stage tradeoff),
      so a failed publish after a successful commit is a known,
      manually-reconciled gap, not a bug.
    """

    @abstractmethod
    async def publish(self, event: RecommendationsGeneratedEvent) -> None:
        """Publishes one outbound RecommendationsGenerated integration event."""
        raise NotImplementedError
