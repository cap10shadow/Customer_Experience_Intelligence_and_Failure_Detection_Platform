import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from backend.services.recommendation_service.app.application.recommendation_statistics_service import (
    RecommendationStatisticsService,
)
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.domain.recommendation_repository import RecommendationRepository
from backend.services.recommendation_service.app.presentation.api.schemas import (
    RecommendationDecisionPatchRequest,
    RecommendationDetailResponse,
    RecommendationStatisticsResponse,
    RecommendationSummaryResponse,
)
from backend.services.recommendation_service.app.presentation.dependencies import (
    get_recommendation_repository,
    get_recommendation_statistics_service,
)
from backend.shared.logging.logger import get_logger
from backend.shared.security.internal_auth import PRINCIPAL_USER_ID_HEADER, require_internal_secret

router = APIRouter(tags=["recommendations"])
logger = get_logger(__name__)

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# NOTE: route order matters -- literal-path routes (`/recommendations/statistics`,
# `/recommendations/generations/{generation_id}`) must be registered before
# the catch-all `/recommendations/{recommendation_id}` route, or FastAPI
# would try to parse "statistics" as a UUID. `/recommendations/generations/{id}`
# has one extra path segment versus `/recommendations/{recommendation_id}`,
# so it never actually collides with the catch-all regardless of order --
# only `/recommendations/statistics` does.


@router.get("/recommendations", response_model=List[RecommendationSummaryResponse])
async def list_recommendations(
    category: Optional[RecommendationCategory] = Query(default=None, description="Optional filter to one category."),
    priority: Optional[RecommendationPriority] = Query(default=None, description="Optional filter to one priority."),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repository: RecommendationRepository = Depends(get_recommendation_repository),
):
    """
    Lists persisted Recommendations, most recent first. Read-only: this
    never executes the Recommendation Engine. `category` and `priority`
    are alternative filters -- if both are supplied, `category` takes
    precedence; if neither is supplied, Recommendations across every
    incident are listed.
    """
    if category is not None:
        records = await repository.list_by_category(category, limit=limit, offset=offset)
    elif priority is not None:
        records = await repository.list_by_priority(priority, limit=limit, offset=offset)
    else:
        records = await repository.list_by_incident(None, limit=limit, offset=offset)
    return [RecommendationSummaryResponse.from_record(record) for record in records]


@router.get("/recommendations/statistics", response_model=RecommendationStatisticsResponse)
async def get_recommendation_statistics(
    statistics_service: RecommendationStatisticsService = Depends(get_recommendation_statistics_service),
):
    """Returns aggregate statistics computed across all persisted Recommendations."""
    statistics = await statistics_service.compute()
    return RecommendationStatisticsResponse(
        total_count=statistics.total_count,
        category_counts=statistics.category_counts,
        priority_counts=statistics.priority_counts,
        average_score=statistics.average_score,
    )


@router.get("/recommendations/generations/{generation_id}", response_model=List[RecommendationSummaryResponse])
async def get_recommendations_by_generation(
    generation_id: uuid.UUID,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repository: RecommendationRepository = Depends(get_recommendation_repository),
):
    """Lists every Recommendation produced by one engine execution (one RecommendationGeneration)."""
    records = await repository.list_by_generation(generation_id, limit=limit, offset=offset)
    return [RecommendationSummaryResponse.from_record(record) for record in records]


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationDetailResponse)
async def get_recommendation(
    recommendation_id: uuid.UUID,
    repository: RecommendationRepository = Depends(get_recommendation_repository),
):
    """Returns a single Recommendation, in full detail, by its own id."""
    record = await repository.get_by_id(recommendation_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return RecommendationDetailResponse.from_record(record)


@router.get("/incidents/{incident_id}/recommendations", response_model=List[RecommendationSummaryResponse])
async def list_recommendations_for_incident(
    incident_id: str,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repository: RecommendationRepository = Depends(get_recommendation_repository),
):
    """Lists every Recommendation ever produced for one incident, across every generation, most recent first."""
    records = await repository.list_by_incident(incident_id, limit=limit, offset=offset)
    return [RecommendationSummaryResponse.from_record(record) for record in records]


@router.get("/incidents/{incident_id}/recommendations/latest", response_model=List[RecommendationSummaryResponse])
async def list_latest_recommendations_for_incident(
    incident_id: str,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repository: RecommendationRepository = Depends(get_recommendation_repository),
):
    """Lists the Recommendations belonging to the most recent engine execution (RecommendationGeneration) for one incident."""
    records = await repository.get_latest_by_incident(incident_id, limit=limit, offset=offset)
    return [RecommendationSummaryResponse.from_record(record) for record in records]


@router.patch(
    "/recommendations/{recommendation_id}/decision",
    response_model=RecommendationDetailResponse,
    dependencies=[Depends(require_internal_secret)],
)
async def update_recommendation_decision(
    recommendation_id: uuid.UUID,
    request: RecommendationDecisionPatchRequest,
    repository: RecommendationRepository = Depends(get_recommendation_repository),
    x_authenticated_user_id: Optional[str] = Header(default=None, alias=PRINCIPAL_USER_ID_HEADER),
):
    """
    Records a human decision against one persisted Recommendation (Step
    7.X G-01) -- the platform's one minimal decision-persistence
    capability. `decided_at` is always set here, server-side, from the
    current time; the request never supplies it. Repeated calls simply
    overwrite the prior decision (see `RecommendationRepository
    .update_decision()`'s own docstring for why that is the correct,
    honest behavior for the current-state row, and how the append-only
    history table answers the "who changed what, when" question this
    row-level overwrite deliberately doesn't).

    Phase 13 Batch 4 (AD-5, §14): this route is a genuine internal
    mutation boundary, requiring `X-Internal-Secret` -- only
    gateway_service is a legitimate caller.

    Phase 13 Batch 5 (AD-3, §14/§15): `x_authenticated_user_id` is the
    Gateway-attested principal, trustworthy only because it arrives
    alongside a valid internal secret. It is now persisted as
    `decided_by` on the current-state row and as `actor_id` on the new
    `recommendation_decision_history` row -- derived exclusively from
    this header, never from `request` (`RecommendationDecisionPatchRequest`
    accepts no actor/owner field at all). A missing or malformed header
    persists `None` ("no known actor"), never a fabricated identity, and
    never fails the request -- the internal-secret check above is the
    request's actual authorization boundary. The response contract is
    unchanged: no `decided_by`/`actor_id` field is added to it (AD-3
    does not require exposing attribution via this API).
    """
    actor_id: Optional[uuid.UUID] = None
    if x_authenticated_user_id:
        try:
            actor_id = uuid.UUID(x_authenticated_user_id)
        except ValueError:
            actor_id = None
        logger.info(
            "Recommendation decision recorded with a Gateway-attested principal.",
            extra={"safe_extra": {"user_id": x_authenticated_user_id, "recommendation_id": str(recommendation_id)}},
        )

    updated = await repository.update_decision(
        recommendation_id,
        decision=request.decision,
        note=request.note,
        decided_at=datetime.now(timezone.utc),
        actor_id=actor_id,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return RecommendationDetailResponse.from_record(updated)
