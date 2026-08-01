from dataclasses import dataclass
from typing import Tuple

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType


@dataclass(frozen=True)
class AnomalyIntelligence:
    """
    Plain, persistence-independent summary of the Phase 5 anomaly signals
    relevant to one Incident, as seen by the Recommendation Engine.

    Deliberately NOT the Anomaly Service's own ORM models, and deliberately
    the same shape Business Impact Service's own `AnomalyMetrics` already
    established for the identical purpose -- reused here as a proven,
    precedent-consistent local value object rather than a new invention.
    `sla_breach_count` and `affected_customer_count` are already-computed
    upstream figures; this engine never recomputes them, only reads them.

    Optional on `IntelligenceContext`: not every Incident necessarily has
    anomaly-level detail attached at recommendation time.
    """

    anomaly_types: Tuple[AnomalyType, ...]
    severity: AnomalySeverity
    affected_customer_count: int
    sla_breach_count: int
    negative_sentiment_ratio: float = 0.0
