import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from backend.services.root_cause_service.app.domain.evidence import EvidenceType
from backend.shared.constants.enums.root_cause import RootCause as RootCauseEnum
from backend.shared.constants.enums.root_cause import RootCauseStatus


class CreateRootCauseRequest(BaseModel):
    """Request body for POST /root-causes: which Incident to analyze."""
    incident_id: uuid.UUID


class EvidenceResponse(BaseModel):
    """One structured, explainable fact behind a RootCause's confidence score."""
    type: EvidenceType
    description: str
    weight: int


class RootCauseResponse(BaseModel):
    """Full explainable snapshot of a persisted RootCause."""

    id: uuid.UUID
    incident_id: uuid.UUID
    cause: RootCauseEnum
    confidence_score: int
    confidence_level: str
    evidence: List[EvidenceResponse]
    explanation: str
    rule_version: str
    status: RootCauseStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
