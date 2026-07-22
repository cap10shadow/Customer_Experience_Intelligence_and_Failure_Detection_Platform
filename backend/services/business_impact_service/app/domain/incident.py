from dataclasses import dataclass
from typing import Tuple

from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.complaint import UrgencyLabel


@dataclass(frozen=True)
class Incident:
    """
    Plain, persistence-independent view of an Incident, as seen by the
    Business Impact Engine.

    Deliberately NOT the Root Cause Service's `Incident` (or the Anomaly
    Service's ORM model): this engine must remain independently deployable
    and must never query another service's domain, a database, or any
    repository/API (Phase 7 Step 1 scope) -- it only ever evaluates the
    plain object it is handed. A later step is responsible for constructing
    this from real incident data.
    """

    incident_id: str
    severity: AnomalySeverity
    regions: Tuple[str, ...] = ()
    urgency_levels: Tuple[UrgencyLabel, ...] = ()
