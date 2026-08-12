import httpx
from fastapi import APIRouter, Depends

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.recommendations import (
    RecommendationDecisionPatchRequest,
    RecommendationResponse,
)
from backend.services.gateway_service.app.services.recommendation_aggregator import (
    build_recommendation,
    update_recommendation_decision,
)

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> RecommendationResponse:
    """
    Recommendation read integration (Part 4): `recommendationId` is the
    resource identity here, not `incidentId` -- the Recommendation
    Workspace's canonical route is `/recommendations/:recommendationId`
    (Batch 4A SS8/SS9). `incidentId` is carried through only as
    traceability metadata on the response.

    A 404 here means the Recommendation genuinely does not exist
    (recommendation_service's own 404, propagated as-is) -- see
    recommendation_aggregator.build_recommendation's docstring.
    """
    return await build_recommendation(client, recommendation_id)


@router.patch("/recommendations/{recommendation_id}/decision", response_model=RecommendationResponse)
async def patch_recommendation_decision(
    recommendation_id: str,
    request: RecommendationDecisionPatchRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> RecommendationResponse:
    """
    Recommendation decision persistence (Step 7.X G-01): forwards the
    real decision to recommendation_service and returns its real,
    updated response. No business logic lives here -- FastAPI/Pydantic
    validates request shape via `RecommendationDecisionPatchRequest`
    (rejecting any unsupported field, including an actor/owner or a
    client-supplied timestamp), and `update_recommendation_decision`
    forwards the request as-is.
    """
    return await update_recommendation_decision(
        client, recommendation_id, decision=request.decision, note=request.note
    )
