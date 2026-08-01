from dataclasses import dataclass
from typing import Tuple

from backend.shared.constants.enums.anomaly import AnomalySeverity
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel


@dataclass(frozen=True)
class Incident:
    """
    Plain, persistence-independent view of an Incident, as seen by the
    Recommendation Engine.

    Deliberately NOT the Anomaly Service's ORM `Incident`, nor Root Cause's
    or Business Impact's own local `Incident` value objects: this engine
    must remain independently deployable and must never import another
    service's domain/ORM classes (DATA-002) -- it only ever evaluates the
    plain object it is handed. A later step is responsible for constructing
    this from real incident data.

    `categories` and `urgency_levels` summarize what the underlying
    (evidence-only) anomalies were about, at the Incident level -- the same
    aggregate-level shape Root Cause's own `Incident` uses. This is
    deliberately a different, coarser granularity than
    `NLPIntelligence.issue_category`/`sentiment_label`, which reflect a
    single representative enrichment rather than an incident-wide summary.
    """

    incident_id: str
    severity: AnomalySeverity
    categories: Tuple[IssueCategory, ...] = ()
    regions: Tuple[str, ...] = ()
    urgency_levels: Tuple[UrgencyLabel, ...] = ()
