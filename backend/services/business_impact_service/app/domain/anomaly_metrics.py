from dataclasses import dataclass
from typing import Tuple

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType


@dataclass(frozen=True)
class AnomalyMetrics:
    """
    Plain, persistence-independent summary of the anomaly signals (Phase 5)
    relevant to one Incident, as seen by the Business Impact Engine.

    `affected_customer_count` and `sla_breach_count` are already-computed
    upstream figures -- this engine never recomputes them, only reads them.
    """

    anomaly_types: Tuple[AnomalyType, ...]
    severity: AnomalySeverity
    affected_customer_count: int
    sla_breach_count: int
    negative_sentiment_ratio: float = 0.0
