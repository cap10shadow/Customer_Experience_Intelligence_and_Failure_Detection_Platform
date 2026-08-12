import httpx
from fastapi import APIRouter, Depends

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.recommendations import RecommendationResponse
from backend.services.gateway_service.app.services.recommendation_aggregator import build_recommendation

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
