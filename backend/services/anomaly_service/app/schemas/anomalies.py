import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyStatus, AnomalyType


class ActiveAnomalyResponse(BaseModel):
    """Full explainable snapshot of an anomaly: current value, baseline, percentage
    change, severity, the rule that fired, and a human-readable explanation."""

    id: uuid.UUID
    fingerprint: str
    type: AnomalyType
    severity: AnomalySeverity
    entity_type: str
    entity_value: Optional[str] = None
    baseline_value: float
    current_value: float
    percentage_change: Optional[float] = None
    triggered_rule: str
    explanation: str
    first_detected_at: datetime
    last_seen_at: datetime
    status: AnomalyStatus

    model_config = ConfigDict(from_attributes=True)


class AnomalyRunItem(BaseModel):
    """One anomaly affected by a detection run, plus why it appears in this run."""

    anomaly: ActiveAnomalyResponse
    reason: str


class AnomalyRunResult(BaseModel):
    """The outcome of a single detection run: everything created, updated, or resolved."""

    run_at: Optional[datetime] = None
    period: Optional[str] = None
    detected: List[AnomalyRunItem] = []
    updated: List[AnomalyRunItem] = []
    resolved: List[AnomalyRunItem] = []
