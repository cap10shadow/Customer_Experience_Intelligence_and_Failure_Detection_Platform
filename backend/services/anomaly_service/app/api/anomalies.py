import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.services.anomaly_service.app.dependencies.services import get_anomaly_engine
from backend.services.anomaly_service.app.services.anomaly_engine import AnomalyEngine
from backend.services.anomaly_service.app.schemas.anomalies import ActiveAnomalyResponse, AnomalyRunResult

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

DaysParam = Query(
    30, ge=1, le=365, description="Size of the trailing window, in days, compared against the equivalent previous window."
)


@router.post("/run", response_model=AnomalyRunResult)
async def run_anomaly_detection(
    days: int = DaysParam,
    engine: AnomalyEngine = Depends(get_anomaly_engine),
):
    """Runs all detectors and reconciles their findings against active anomalies."""
    return await engine.run(days)


# NOTE: "/latest" must be registered before "/{anomaly_id}" — otherwise
# FastAPI would try to parse the literal string "latest" as a UUID.
@router.get("/latest", response_model=AnomalyRunResult)
async def get_latest_run(
    engine: AnomalyEngine = Depends(get_anomaly_engine),
):
    """Returns the outcome of the most recent detection run, without re-running detection."""
    return await engine.get_latest()


@router.get("", response_model=List[ActiveAnomalyResponse])
async def list_active_anomalies(
    engine: AnomalyEngine = Depends(get_anomaly_engine),
):
    """Returns all currently active anomalies."""
    return await engine.get_active()


@router.get("/{anomaly_id}", response_model=ActiveAnomalyResponse)
async def get_anomaly(
    anomaly_id: uuid.UUID,
    engine: AnomalyEngine = Depends(get_anomaly_engine),
):
    """Returns full explainable details for a single anomaly."""
    anomaly = await engine.get_by_id(anomaly_id)
    if anomaly is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found")
    return anomaly
