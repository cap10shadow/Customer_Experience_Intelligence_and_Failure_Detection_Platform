import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.services.anomaly_service.app.dependencies.services import get_correlation_engine
from backend.services.anomaly_service.app.services.correlation_engine import CorrelationEngine
from backend.services.anomaly_service.app.schemas.anomalies import ActiveAnomalyResponse
from backend.services.anomaly_service.app.schemas.incidents import IncidentResponse, IncidentRunResult
from backend.services.anomaly_service.app.services.scoring import DEFAULT_TIME_WINDOW_MINUTES

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/run", response_model=IncidentRunResult)
async def run_incident_correlation(
    dataset_id: uuid.UUID = Query(..., description="The Dataset this correlation run is scoped to."),
    dataset_version_id: uuid.UUID = Query(
        ..., description="The DatasetVersion this run's results are attributed to (provenance)."
    ),
    window_minutes: int = Query(
        DEFAULT_TIME_WINDOW_MINUTES,
        ge=1,
        le=1440,
        description="Temporal proximity window, in minutes, used to cluster candidate anomalies.",
    ),
    engine: CorrelationEngine = Depends(get_correlation_engine),
):
    """Runs the deterministic correlation engine over one dataset's active anomalies and returns what changed."""
    return await engine.run(dataset_id, dataset_version_id, window_minutes)


@router.get("", response_model=List[IncidentResponse])
async def list_active_incidents(
    dataset_id: uuid.UUID = Query(..., description="The Dataset to list open incidents for."),
    engine: CorrelationEngine = Depends(get_correlation_engine),
):
    """Returns all currently open incidents for this dataset."""
    return await engine.get_active(dataset_id)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    engine: CorrelationEngine = Depends(get_correlation_engine),
):
    """Returns full explainable details for a single incident."""
    incident = await engine.get_by_id(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.get("/{incident_id}/anomalies", response_model=List[ActiveAnomalyResponse])
async def get_incident_anomalies(
    incident_id: uuid.UUID,
    engine: CorrelationEngine = Depends(get_correlation_engine),
):
    """Returns the active anomalies linked as evidence for this incident."""
    anomalies = await engine.get_anomalies_for_incident(incident_id)
    if anomalies is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return anomalies
