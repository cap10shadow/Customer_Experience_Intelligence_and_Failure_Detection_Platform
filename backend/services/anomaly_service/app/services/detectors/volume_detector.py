from typing import List

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.services.explainability import build_explanation
from backend.services.anomaly_service.app.services.fingerprint import AnomalyCandidate
from backend.services.anomaly_service.app.services.severity import describe_rule, evaluate_change
from backend.services.anomaly_service.app.utils.time_window import TrendWindow
from backend.shared.constants.enums.anomaly import AnomalyType

ENTITY_TYPE = "global"


class VolumeDetector:
    """
    Detects an overall complaint volume spike: total complaint count in the
    current window vs the previous equivalent window. Single responsibility:
    this detector only reasons about total volume, not any breakdown.
    """

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def detect(self, current: TrendWindow, previous: TrendWindow) -> List[AnomalyCandidate]:
        current_rows = await self.repository.count_complaints_by_day(current.start, current.end)
        previous_rows = await self.repository.count_complaints_by_day(previous.start, previous.end)

        current_total = sum(count for _, count in current_rows)
        baseline_total = sum(count for _, count in previous_rows)

        result = evaluate_change(baseline_total, current_total, direction="increase")
        if result is None:
            return []
        percentage_change, severity = result

        explanation = build_explanation(
            AnomalyType.COMPLAINT_SPIKE, ENTITY_TYPE, None, baseline_total, current_total, percentage_change, severity
        )
        return [
            AnomalyCandidate(
                type=AnomalyType.COMPLAINT_SPIKE,
                entity_type=ENTITY_TYPE,
                entity_value=None,
                baseline_value=baseline_total,
                current_value=current_total,
                percentage_change=percentage_change,
                severity=severity,
                triggered_rule=describe_rule(severity, percentage_change),
                explanation=explanation,
            )
        ]
