from typing import List

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.services.explainability import build_explanation
from backend.services.anomaly_service.app.services.fingerprint import AnomalyCandidate
from backend.services.anomaly_service.app.services.severity import describe_rule, evaluate_change
from backend.services.anomaly_service.app.utils.time_window import TrendWindow
from backend.shared.constants.enums.anomaly import AnomalyType

ENTITY_TYPE = "region"


class RegionDetector:
    """
    Detects a complaint volume spike within a single customer region:
    per-region count in the current window vs the previous equivalent
    window. Single responsibility: region dimension only.
    """

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def detect(self, current: TrendWindow, previous: TrendWindow) -> List[AnomalyCandidate]:
        current_rows = await self.repository.count_complaints_by_region(current.start, current.end)
        previous_rows = await self.repository.count_complaints_by_region(previous.start, previous.end)

        current_counts = dict(current_rows)
        baseline_counts = dict(previous_rows)

        candidates: List[AnomalyCandidate] = []
        for region in sorted(set(current_counts) | set(baseline_counts)):
            current_value = current_counts.get(region, 0)
            baseline_value = baseline_counts.get(region, 0)

            result = evaluate_change(baseline_value, current_value, direction="increase")
            if result is None:
                continue
            percentage_change, severity = result

            explanation = build_explanation(
                AnomalyType.REGIONAL_SPIKE, ENTITY_TYPE, region, baseline_value, current_value, percentage_change, severity
            )
            candidates.append(
                AnomalyCandidate(
                    type=AnomalyType.REGIONAL_SPIKE,
                    entity_type=ENTITY_TYPE,
                    entity_value=region,
                    baseline_value=baseline_value,
                    current_value=current_value,
                    percentage_change=percentage_change,
                    severity=severity,
                    triggered_rule=describe_rule(severity, percentage_change),
                    explanation=explanation,
                )
            )
        return candidates
