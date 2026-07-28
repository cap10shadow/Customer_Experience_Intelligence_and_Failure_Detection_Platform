from abc import ABC, abstractmethod

from backend.services.evaluation_service.app.application.dto.evaluation_completed_event import (
    EvaluationCompletedEvent,
)


class EventPublisher(ABC):
    """
    Event Publisher (Application-owned port)

    Operational Purpose:
    Defines the outbound-integration-event contract `EvaluationLifecycleService`
    depends on, without depending on any messaging technology itself.
    Infrastructure implements this interface; publishing *decisions*
    (whether/when to publish) remain entirely owned by
    `EvaluationLifecycleService` -- this port only ever transmits what it is
    told to, exactly as `EvaluationRepository` only ever persists what it is
    handed. Same Dependency Inversion the Repository already established for
    this service, applied to the Publisher.

    Architectural Boundaries:
    - `publish()` is called only after a successful commit -- never before,
      never speculatively. If it raises, the caller (`EvaluationLifecycleService`)
      logs at CRITICAL severity and does not retry or roll anything back:
      the Outbox Pattern is intentionally not implemented (accepted
      prototype-stage tradeoff), so a failed publish after a successful
      commit is a known, manually-reconciled gap, not a bug.
    """

    @abstractmethod
    async def publish(self, event: EvaluationCompletedEvent) -> None:
        """Publishes one outbound EvaluationCompleted integration event."""
        raise NotImplementedError
