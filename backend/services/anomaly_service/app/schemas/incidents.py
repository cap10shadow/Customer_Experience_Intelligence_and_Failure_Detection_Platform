import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.incident import IncidentStatus


class IncidentResponse(BaseModel):
    """Full explainable snapshot of an incident: confidence score, human-readable
    summary, and aggregate severity — all derived from its linked anomalies."""

    id: uuid.UUID
    incident_key: str
    title: str
    severity: AnomalySeverity
    status: IncidentStatus
    confidence_score: int
    summary: str
    started_at: datetime
    last_updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IncidentRunItem(BaseModel):
    """One incident affected by a correlation run, plus why it appears in this run."""

    incident: IncidentResponse
    linked_anomaly_count: int
    reason: str


class IncidentRunResult(BaseModel):
    """The outcome of a single correlation run: every incident created, updated, or resolved."""

    run_at: Optional[datetime] = None
    created: List[IncidentRunItem] = []
    updated: List[IncidentRunItem] = []
    resolved: List[IncidentRunItem] = []
