import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx

from backend.services.business_impact_service.app.models.business_impact_assessment import (
    BusinessImpactAssessmentEntity,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.observability.correlation import correlation_headers

logger = logging.getLogger(__name__)

_EVENT_PATH = "/internal/events/business-impact-completed"


@dataclass(frozen=True)
class BusinessImpactCompletedEvent:
    """
    One BusinessImpactCompleted occurrence, ready to be delivered to both
    consumers.

    `event_id` identifies this event occurrence -- minted once, delivered
    unchanged to both destinations, and never reused across occurrences.
    `incident_id` identifies the incident/business investigation the event
    concerns. These are deliberately kept semantically distinct (Part 6
    requirement): `incident_id` is never substituted for `event_id`.
    """

    event_id: uuid.UUID
    incident_id: uuid.UUID
    incident_severity: AnomalySeverity
    assessment: BusinessImpactAssessmentEntity
    root_cause: PersistedRootCause


@dataclass(frozen=True)
class DeliveryResult:
    """The outcome of one delivery attempt to one consumer -- never raised, always returned."""

    destination: str
    delivered: bool
    detail: str


def build_recommendation_payload(event: BusinessImpactCompletedEvent) -> Dict[str, Any]:
    """
    Shapes the event for recommendation_service's existing, frozen
    `BusinessImpactCompletedPayload` (nested `incident`/`business_impact`/
    `root_cause`). `nlp_intelligence`/`anomaly_intelligence` are
    legitimately omitted -- both are Optional on that schema and
    business_impact_service has no source of either today; omitting them
    is not the same as fabricating an empty one.
    """
    assessment = event.assessment
    return {
        "event_id": str(event.event_id),
        "incident": {
            "incident_id": str(event.incident_id),
            "severity": event.incident_severity.value,
        },
        "business_impact": {
            "business_score": assessment.overall_score,
            "overall_severity": assessment.overall_severity.value,
            "business_priority": assessment.business_priority.value,
            "confidence": assessment.confidence,
            "financial_impact": assessment.financial.value,
            "customer_impact": assessment.customer.value,
            "operational_impact": assessment.operational.value,
            "sla_impact": assessment.sla.value,
            "reputation_impact": assessment.reputation.value,
        },
        "root_cause": {
            "cause": event.root_cause.cause.value,
            "confidence_score": event.root_cause.confidence_score,
            "confidence_level": event.root_cause.confidence_level,
        },
    }


def build_evaluation_payload(event: BusinessImpactCompletedEvent) -> Dict[str, Any]:
    """Shapes the event for evaluation_service's existing, frozen flat `BusinessImpactCompletedPayload`."""
    assessment = event.assessment
    root_cause = event.root_cause
    return {
        "event_id": str(event.event_id),
        "incident_id": str(event.incident_id),
        "root_cause": root_cause.cause.value,
        "root_cause_confidence_score": root_cause.confidence_score,
        "root_cause_explanation": root_cause.explanation,
        "root_cause_evidence_count": len(root_cause.evidence),
        "root_cause_id": str(root_cause.id),
        "business_impact_overall_score": assessment.overall_score,
        "business_impact_overall_severity": assessment.overall_severity.value,
        "business_impact_business_priority": assessment.business_priority.value,
        "business_impact_confidence": assessment.confidence,
        "business_impact_explanation": assessment.explanation,
        "assessment_id": str(assessment.assessment_id),
    }


class BusinessImpactEventPublisher:
    """
    Delivers one BusinessImpactCompleted occurrence to recommendation_service
    and evaluation_service independently -- a parallel fan-out (Batch 4B
    SS2/SS5), never a chain: neither destination's delivery is made to wait
    on, or depend on the outcome of, the other.

    Prototype delivery guarantee (Part 6, explicit per the frozen
    architecture's own Batch 4B SS6 scope): this is single-attempt,
    best-effort HTTP delivery with NO retry, NO outbox, and NO durable
    queue -- there is no broker anywhere in this repository. If a delivery
    attempt fails (timeout, connection error, non-2xx), that occurrence of
    the event is simply not delivered to that consumer; nothing here
    redelivers it later. This is weaker than the "at-least-once" target the
    frozen architecture describes for a production deployment, and is
    documented here rather than silently assumed to be stronger than it
    actually is. Failures are logged, never silently treated as success.
    """

    def __init__(self, client: httpx.AsyncClient, *, recommendation_url: str, evaluation_url: str, timeout_seconds: float) -> None:
        self._client = client
        self._recommendation_url = recommendation_url.rstrip("/")
        self._evaluation_url = evaluation_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def publish(self, event: BusinessImpactCompletedEvent) -> List[DeliveryResult]:
        """
        Issues both deliveries concurrently via a single `asyncio.gather`
        call. Each delivery is caught and converted to a `DeliveryResult`
        inside `_deliver` itself, so one destination's exception can never
        cancel or block the other's request -- gather here is purely for
        concurrency, not for exception propagation.
        """
        return list(
            await asyncio.gather(
                self._deliver(
                    "recommendation_service",
                    f"{self._recommendation_url}{_EVENT_PATH}",
                    build_recommendation_payload(event),
                ),
                self._deliver(
                    "evaluation_service",
                    f"{self._evaluation_url}{_EVENT_PATH}",
                    build_evaluation_payload(event),
                ),
            )
        )

    async def _deliver(self, destination: str, url: str, body: Dict[str, Any]) -> DeliveryResult:
        try:
            response = await self._client.post(
                url, json=body, timeout=self._timeout_seconds, headers=correlation_headers()
            )
        except httpx.TimeoutException as exc:
            logger.warning("BusinessImpactCompleted delivery to %s timed out: %s", destination, exc)
            return DeliveryResult(destination=destination, delivered=False, detail="timeout")
        except httpx.HTTPError as exc:
            logger.warning("BusinessImpactCompleted delivery to %s failed: %s", destination, exc)
            return DeliveryResult(destination=destination, delivered=False, detail="connection_error")

        if response.status_code >= 400:
            logger.warning(
                "BusinessImpactCompleted delivery to %s returned status %s: %s",
                destination,
                response.status_code,
                response.text,
            )
            return DeliveryResult(destination=destination, delivered=False, detail=f"http_{response.status_code}")

        return DeliveryResult(destination=destination, delivered=True, detail="delivered")
