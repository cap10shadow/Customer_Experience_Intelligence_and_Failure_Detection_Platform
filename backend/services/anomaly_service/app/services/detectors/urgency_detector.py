from typing import List

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.services.explainability import build_explanation
from backend.services.anomaly_service.app.services.fingerprint import AnomalyCandidate
from backend.services.anomaly_service.app.services.severity import describe_rule, evaluate_change
from backend.services.anomaly_service.app.utils.time_window import TrendWindow
from backend.shared.constants.enums.anomaly import AnomalyType

ENTITY_TYPE = "urgency"


class UrgencyDetector:
    """
    Detects a spike within a single urgency level: per-urgency-level count
    in the current window vs the previous equivalent window. Single
    responsibility: urgency dimension only.
    """

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def detect(self, current: TrendWindow, previous: TrendWindow) -> List[AnomalyCandidate]:
        current_rows = await self.repository.count_enrichments_by_urgency(current.start, current.end)
        previous_rows = await self.repository.count_enrichments_by_urgency(previous.start, previous.end)

        current_counts = {urgency.value: count for urgency, count in current_rows}
        baseline_counts = {urgency.value: count for urgency, count in previous_rows}

        candidates: List[AnomalyCandidate] = []
        for urgency in sorted(set(current_counts) | set(baseline_counts)):
            current_value = current_counts.get(urgency, 0)
            baseline_value = baseline_counts.get(urgency, 0)

            result = evaluate_change(baseline_value, current_value, direction="increase")
            if result is None:
                continue
            percentage_change, severity = result

            explanation = build_explanation(
                AnomalyType.URGENCY_SPIKE, ENTITY_TYPE, urgency, baseline_value, current_value, percentage_change, severity
            )
            candidates.append(
                AnomalyCandidate(
                    type=AnomalyType.URGENCY_SPIKE,
                    entity_type=ENTITY_TYPE,
                    entity_value=urgency,
                    baseline_value=baseline_value,
                    current_value=current_value,
                    percentage_change=percentage_change,
                    severity=severity,
                    triggered_rule=describe_rule(severity, percentage_change),
                    explanation=explanation,
                )
            )
        return candidates
