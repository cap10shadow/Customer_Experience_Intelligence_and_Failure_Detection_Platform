from fastapi import APIRouter, Depends, Request

from backend.services.recommendation_service.app.infrastructure.messaging.consumers.business_impact_completed_consumer import (
    BusinessImpactCompletedConsumer,
)
from backend.services.recommendation_service.app.presentation.dependencies import get_business_impact_completed_consumer

router = APIRouter(prefix="/internal/events", tags=["internal-events"])


@router.post("/business-impact-completed", status_code=202)
async def handle_business_impact_completed(
    request: Request,
    consumer: BusinessImpactCompletedConsumer = Depends(get_business_impact_completed_consumer),
):
    """
    In-process entry point for the BusinessImpactCompleted event, standing
    in for a real message broker subscription -- none exists anywhere in
    this repository yet (the same, still-current finding
    `evaluation_service`'s own Step 3 made before implementation began).
    This route contains no logic of its own: it reads the raw JSON body
    exactly as an untyped broker message payload would arrive (deliberately
    not FastAPI/Pydantic-validated -- that deserialization is
    `BusinessImpactCompletedConsumer`'s own Infrastructure responsibility,
    not this route's) and hands it directly to the Consumer.

    Not mounted under `/api/v1`: this is an internal execution-lifecycle
    trigger, not part of the public, read-only Recommendation API.

    The HTTP status code doubles as the retry signal a future broker
    integration would act on: a 2xx response means a terminal outcome was
    reached (COMPLETED or REJECTED) and must not be retried; an unhandled
    exception propagating out of the Consumer surfaces as a 5xx, signaling
    a transient infrastructure failure that a real broker would retry per
    its own policy.
    """
    raw_payload = await request.json()
    result = await consumer.consume(raw_payload)
    return {
        "outcome": result.outcome.value,
        "generation_id": str(result.generation_id) if result.generation_id else None,
        "recommendation_count": result.recommendation_count,
        "reason": result.reason,
    }
