from typing import List, Optional

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.services.explainability import build_explanation
from backend.services.anomaly_service.app.services.fingerprint import AnomalyCandidate
from backend.services.anomaly_service.app.services.severity import describe_rule, evaluate_change
from backend.services.anomaly_service.app.utils.constants import SENTIMENT_SCORES
from backend.services.anomaly_service.app.utils.time_window import TrendWindow
from backend.shared.constants.enums.anomaly import AnomalyType

ENTITY_TYPE = "global"


class SentimentDetector:
    """
    Detects overall sentiment deterioration: the average sentiment score
    (via the existing ordinal SENTIMENT_SCORES mapping — not recomputed) in
    the current window vs the previous equivalent window. Only a decline is
    considered anomalous; an improving average is not flagged. Single
    responsibility: overall sentiment trend only.
    """

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def detect(self, current: TrendWindow, previous: TrendWindow) -> List[AnomalyCandidate]:
        current_avg = await self._average_sentiment(current)
        baseline_avg = await self._average_sentiment(previous)

        # No enrichment data in one of the windows: there is nothing
        # reliable to compare against, so nothing is reported.
        if current_avg is None or baseline_avg is None:
            return []

        result = evaluate_change(baseline_avg, current_avg, direction="decrease")
        if result is None:
            return []
        percentage_change, severity = result

        explanation = build_explanation(
            AnomalyType.SENTIMENT_SHIFT, ENTITY_TYPE, None, baseline_avg, current_avg, percentage_change, severity
        )
        return [
            AnomalyCandidate(
                type=AnomalyType.SENTIMENT_SHIFT,
                entity_type=ENTITY_TYPE,
                entity_value=None,
                baseline_value=baseline_avg,
                current_value=current_avg,
                percentage_change=percentage_change,
                severity=severity,
                triggered_rule=describe_rule(severity, percentage_change),
                explanation=explanation,
            )
        ]

    async def _average_sentiment(self, window: TrendWindow) -> Optional[float]:
        """Returns the count-weighted average sentiment score, or None if there is no data."""
        rows = await self.repository.count_enrichments_by_day_and_sentiment(window.start, window.end)
        weighted_sum = 0
        total = 0
        for _day, label, count in rows:
            weighted_sum += SENTIMENT_SCORES[label] * count
            total += count
        return weighted_sum / total if total > 0 else None
