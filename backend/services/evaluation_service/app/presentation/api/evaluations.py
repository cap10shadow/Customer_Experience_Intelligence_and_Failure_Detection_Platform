import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.services.evaluation_service.app.application.evaluation_statistics_service import (
    EvaluationStatisticsService,
)
from backend.services.evaluation_service.app.domain.evaluation_repository import EvaluationRepository
from backend.services.evaluation_service.app.presentation.api.schemas import (
    EvaluationResponse,
    EvaluationStatisticsResponse,
)
from backend.services.evaluation_service.app.presentation.dependencies import (
    get_evaluation_repository,
    get_evaluation_statistics_service,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# NOTE: route order matters -- literal-path routes (`/statistics`,
# `/latest/{incident_id}`, `/history/{incident_id}`) must be registered
# before the catch-all `/{evaluation_id}` route, or FastAPI would try to
# parse "statistics" as a UUID.


@router.get("", response_model=List[EvaluationResponse])
async def list_evaluations(
    incident_id: Optional[str] = Query(default=None, description="Optional filter to one incident's Evaluations."),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repository: EvaluationRepository = Depends(get_evaluation_repository),
):
    """Lists persisted Evaluations, most recent first, optionally filtered by incident_id. Read-only: this never executes an evaluation."""
    records = await repository.list_by_incident(incident_id, limit=limit, offset=offset)
    return [EvaluationResponse.from_record(record) for record in records]


@router.get("/statistics", response_model=EvaluationStatisticsResponse)
async def get_evaluation_statistics(
    statistics_service: EvaluationStatisticsService = Depends(get_evaluation_statistics_service),
):
    """Returns aggregate statistics computed across all persisted Evaluations."""
    statistics = await statistics_service.compute()
    return EvaluationStatisticsResponse(
        total_count=statistics.total_count,
        quality_rating_counts=statistics.quality_rating_counts,
        explainability_rating_counts=statistics.explainability_rating_counts,
        average_quality_score=statistics.average_quality_score,
        average_explainability_score=statistics.average_explainability_score,
        average_confidence=statistics.average_confidence,
    )


@router.get("/latest/{incident_id}", response_model=EvaluationResponse)
async def get_latest_evaluation(
    incident_id: str,
    repository: EvaluationRepository = Depends(get_evaluation_repository),
):
    """Returns the most recent Evaluation for the given incident."""
    record = await repository.get_latest(incident_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Evaluation found for this incident")
    return EvaluationResponse.from_record(record)


@router.get("/history/{incident_id}", response_model=List[EvaluationResponse])
async def get_evaluation_history(
    incident_id: str,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    repository: EvaluationRepository = Depends(get_evaluation_repository),
):
    """Lists every Evaluation ever recorded for one incident, ordered by evaluation lineage (most recent first)."""
    records = await repository.list_history(incident_id, limit=limit, offset=offset)
    return [EvaluationResponse.from_record(record) for record in records]


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    repository: EvaluationRepository = Depends(get_evaluation_repository),
):
    """Returns a single Evaluation by its own id."""
    record = await repository.get_by_id(evaluation_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return EvaluationResponse.from_record(record)
