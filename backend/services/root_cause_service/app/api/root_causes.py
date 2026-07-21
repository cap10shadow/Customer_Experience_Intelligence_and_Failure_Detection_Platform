import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.services.root_cause_service.app.dependencies.services import get_root_cause_application_service
from backend.services.root_cause_service.app.schemas.root_cause import CreateRootCauseRequest, RootCauseResponse
from backend.services.root_cause_service.app.services.exceptions import (
    IncidentNotFoundError,
    RootCauseAlreadyExistsError,
)
from backend.services.root_cause_service.app.services.root_cause_application_service import RootCauseApplicationService

router = APIRouter(prefix="/root-causes", tags=["root-causes"])

# Nested under /incidents rather than /root-causes — kept in this module
# since it serves the same resource and application service.
incidents_router = APIRouter(prefix="/incidents", tags=["root-causes"])


@router.post("", response_model=RootCauseResponse, status_code=status.HTTP_201_CREATED)
async def create_root_cause(
    request: CreateRootCauseRequest,
    service: RootCauseApplicationService = Depends(get_root_cause_application_service),
):
    """
    Runs Root Cause Analysis for an Incident and persists the result.

    Idempotent creation is intentionally not supported: if a RootCause
    already exists for this incident, this returns 409 Conflict rather than
    an upsert — recalculation belongs to Phase 6 Step 3.
    """
    try:
        root_cause = await service.create_root_cause(request.incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RootCauseAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return root_cause


@router.get("/{root_cause_id}", response_model=RootCauseResponse)
async def get_root_cause(
    root_cause_id: uuid.UUID,
    service: RootCauseApplicationService = Depends(get_root_cause_application_service),
):
    """Returns a RootCause by its own ID."""
    root_cause = await service.get_root_cause(root_cause_id)
    if root_cause is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RootCause not found")
    return root_cause


@router.get("", response_model=List[RootCauseResponse])
async def list_root_causes(
    service: RootCauseApplicationService = Depends(get_root_cause_application_service),
):
    """Returns all persisted RootCause records. Filtering is deferred to a later step."""
    return await service.list_root_causes()


@incidents_router.get("/{incident_id}/root-cause", response_model=RootCauseResponse)
async def get_root_cause_by_incident(
    incident_id: uuid.UUID,
    service: RootCauseApplicationService = Depends(get_root_cause_application_service),
):
    """Returns the RootCause linked to a given Incident."""
    root_cause = await service.get_root_cause_by_incident(incident_id)
    if root_cause is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RootCause not found for this incident")
    return root_cause
