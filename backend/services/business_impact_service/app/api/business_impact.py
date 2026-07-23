import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.services.business_impact_service.app.dependencies.services import (
    get_business_impact_application_service,
)
from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.schemas.business_impact import (
    BusinessImpactAssessmentResponse,
    CreateBusinessImpactRequest,
)
from backend.services.business_impact_service.app.services.business_impact_application_service import (
    BusinessImpactApplicationService,
)
from backend.services.business_impact_service.app.services.exceptions import (
    IncidentNotFoundError,
    RootCauseNotFoundError,
)

router = APIRouter(prefix="/business-impact", tags=["business-impact"])


@router.post("", response_model=BusinessImpactAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_business_impact_assessment(
    request: CreateBusinessImpactRequest,
    service: BusinessImpactApplicationService = Depends(get_business_impact_application_service),
):
    """
    Runs Business Impact Analysis for an Incident and persists the result.

    The client supplies only `incident_id` -- the Application Service loads
    the Incident (with its linked anomalies) and its identified RootCause,
    maps them into the (frozen) Business Impact Engine's input value
    objects, and persists the resulting assessment. Assessments are
    immutable snapshots: re-running this for the same incident creates a
    new assessment rather than overwriting a prior one.
    """
    try:
        assessment = await service.create_assessment(request.incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RootCauseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return assessment


@router.get("/{assessment_id}", response_model=BusinessImpactAssessmentResponse)
async def get_business_impact_assessment(
    assessment_id: uuid.UUID,
    service: BusinessImpactApplicationService = Depends(get_business_impact_application_service),
):
    """Returns a BusinessImpactAssessment by its own ID."""
    assessment = await service.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BusinessImpactAssessment not found")
    return assessment


@router.get("", response_model=List[BusinessImpactAssessmentResponse])
async def list_business_impact_assessments(
    severity: Optional[ImpactLevel] = Query(default=None),
    priority: Optional[BusinessPriority] = Query(default=None),
    incident_id: Optional[uuid.UUID] = Query(default=None),
    service: BusinessImpactApplicationService = Depends(get_business_impact_application_service),
):
    """Returns persisted BusinessImpactAssessment records, optionally filtered by severity, priority, and/or incident."""
    return await service.list_assessments(severity=severity, priority=priority, incident_id=incident_id)
