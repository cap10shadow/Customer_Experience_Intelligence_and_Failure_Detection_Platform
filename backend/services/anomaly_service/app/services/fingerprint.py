from dataclasses import dataclass
from typing import Optional

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType


@dataclass(frozen=True)
class AnomalyCandidate:
    """
    A detector's finding for one dimension in one detection run.

    Not persisted directly — the Anomaly Engine reconciles candidates
    against `active_anomalies` by fingerprint to decide whether to create,
    update, or leave a row alone, and determines resolution for any active
    anomaly whose fingerprint no longer appears in a run's candidates.
    """
    type: AnomalyType
    entity_type: str
    entity_value: Optional[str]
    baseline_value: float
    current_value: float
    percentage_change: Optional[float]
    severity: AnomalySeverity
    triggered_rule: str
    explanation: str


def compute_fingerprint(type_: AnomalyType, entity_type: str, entity_value: Optional[str]) -> str:
    """
    Deterministically identifies an anomaly by its detection dimensions.

    Stable across runs by construction: the same (type, entity_type,
    entity_value) always produces the same fingerprint, independent of
    current/baseline values or severity. A plain delimited string is used
    instead of a hash so fingerprints stay human-readable in the database
    and API responses.
    """
    return f"{type_.value}:{entity_type}:{entity_value if entity_value is not None else 'ALL'}"
