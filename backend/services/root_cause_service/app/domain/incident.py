from dataclasses import dataclass
from typing import Tuple

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel


@dataclass(frozen=True)
class Incident:
    """
    Plain, persistence-independent view of an Incident, as seen by the Root
    Cause Rule Engine.

    Deliberately NOT the Anomaly Service's ORM `Incident` model: this
    engine must remain independently deployable and must never query
    anomalies, a database, or any repository/API (Phase 6 Step 1 scope) —
    it only ever evaluates the plain object it is handed. A later step is
    responsible for constructing this from real incident/anomaly data.

    `categories`, `regions`, `urgency_levels`, and `anomaly_types` summarize
    what the underlying (evidence-only) anomalies were about — e.g. which
    issue categories, regions, urgency levels, and anomaly types were
    represented — without carrying any anomaly rows themselves.
    """

    incident_key: str
    title: str
    summary: str
    severity: AnomalySeverity
    confidence_score: int
    categories: Tuple[IssueCategory, ...] = ()
    regions: Tuple[str, ...] = ()
    urgency_levels: Tuple[UrgencyLabel, ...] = ()
    anomaly_types: Tuple[AnomalyType, ...] = ()
