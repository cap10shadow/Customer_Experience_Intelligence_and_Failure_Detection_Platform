from typing import Any, Dict, Optional

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json, patch_json
from backend.services.gateway_service.app.core.errors import ResourceNotFoundError
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.schemas.recommendations import RecommendationResponse, SupportingEvidenceDTO
from backend.shared.security.internal_auth import PRINCIPAL_USER_ID_HEADER, internal_service_headers


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


async def update_recommendation_decision(
    client: httpx.AsyncClient, recommendation_id: str, *, decision: str, note: Optional[str], principal: AuthenticatedUser
) -> RecommendationResponse:
    """
    Records a decision against one Recommendation (Step 7.X G-01) by
    forwarding the real PATCH request to recommendation_service and
    mapping its response back into the public Gateway DTO. Like
    `build_recommendation`, a missing recommendation is essential, not
    degraded -- a genuine downstream 404 becomes a real Gateway 404, never
    fabricated success data. The Gateway performs no business logic here;
    it validates request shape (via `RecommendationDecisionPatchRequest`)
    and forwards the real request, exactly as G-01's design requires.

    Phase 13 Batch 4 (AD-5, §14): this route is a genuine internal
    mutation boundary, so it carries the shared internal-service
    credential, plus the Gateway-attested `principal.user_id` (never
    `principal.email`/`roles` -- only the field §14 approves) so a
    future attribution batch can trust it. recommendation_service does
    not yet persist this value (that is explicitly a later batch's
    scope); this batch only makes the header trustworthy and available.
    """
    updated = await patch_json(
        client,
        f"{settings.RECOMMENDATION_SERVICE_URL}/api/v1/recommendations/{recommendation_id}/decision",
        json={"decision": decision, "note": note},
        extra_headers={**internal_service_headers(), PRINCIPAL_USER_ID_HEADER: str(principal.user_id)},
    )
    if updated is None:
        raise ResourceNotFoundError(
            f"Recommendation {recommendation_id} was not found.",
            details={"recommendationId": recommendation_id},
        )
    return _to_response(updated)


def _to_response(recommendation: Dict[str, Any]) -> RecommendationResponse:
    return RecommendationResponse(
        recommendationId=str(recommendation["recommendation_id"]),
        incidentId=str(recommendation["incident_id"]),
        datasetId=str(recommendation["dataset_id"]),
        datasetVersionId=str(recommendation["dataset_version_id"]),
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
        decision=recommendation.get("decision"),
        decisionNote=recommendation.get("decision_note"),
        decidedAt=str(recommendation["decided_at"]) if recommendation.get("decided_at") is not None else None,
    )
