from typing import Any, Dict

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json
from backend.services.gateway_service.app.core.errors import ResourceNotFoundError
from backend.services.gateway_service.app.schemas.recommendations import RecommendationResponse, SupportingEvidenceDTO


async def build_recommendation(client: httpx.AsyncClient, recommendation_id: str) -> RecommendationResponse:
    """
    Retrieves one Recommendation from recommendation_service and maps it to
    the public Gateway DTO. Unlike Investigation, this is a single
    essential downstream call, not a multi-service aggregation -- the real
    backend capability here (RecommendationDetailResponse) is already a
    complete, self-contained read (Batch 4A SS8).

    A missing recommendation is essential, not degraded: a genuine
    recommendation_service 404 is propagated as a real Gateway 404
    (ResourceNotFoundError), never a generic downstream failure and never
    fabricated placeholder data.
    """
    recommendation = await get_json(
        client, f"{settings.RECOMMENDATION_SERVICE_URL}/api/v1/recommendations/{recommendation_id}"
    )
    if recommendation is None:
        raise ResourceNotFoundError(
            f"Recommendation {recommendation_id} was not found.",
            details={"recommendationId": recommendation_id},
        )
    return _to_response(recommendation)


def _to_response(recommendation: Dict[str, Any]) -> RecommendationResponse:
    return RecommendationResponse(
        recommendationId=str(recommendation["recommendation_id"]),
        incidentId=str(recommendation["incident_id"]),
        generationId=str(recommendation["generation_id"]),
        category=str(recommendation["category"]),
        priority=str(recommendation["priority"]),
        score=recommendation["score"],
        action=recommendation["action"],
        recommendationRationale=recommendation["recommendation_rationale"],
        priorityRationale=recommendation["priority_rationale"],
        supportingEvidence=[
            SupportingEvidenceDTO(source=item["source"], description=item["description"], weight=item["weight"])
            for item in recommendation.get("supporting_evidence", [])
        ],
        createdAt=str(recommendation["created_at"]),
    )
