from collections import OrderedDict
from datetime import date
from typing import Dict, List, TypedDict

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.schemas.trends import SentimentTrendPoint
from backend.services.anomaly_service.app.utils.constants import SENTIMENT_SCORES
from backend.services.anomaly_service.app.utils.time_window import TrendWindow


class _DailySentimentBucket(TypedDict):
    weighted_sum: int
    total: int
    label_counts: Dict[str, int]


class SentimentAggregator:
    """
    Computes average sentiment over time from existing enrichment records.

    Does not recompute sentiment: it only averages the sentiment label each
    complaint was already classified with, using an ordinal scale to turn the
    categorical label into a trend-friendly number.
    """

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def aggregate(self, window: TrendWindow) -> List[SentimentTrendPoint]:
        rows = await self.repository.count_enrichments_by_day_and_sentiment(window.start, window.end)

        by_day: "OrderedDict[date, _DailySentimentBucket]" = OrderedDict()
        for day, label, count in rows:
            bucket = by_day.setdefault(day, {"weighted_sum": 0, "total": 0, "label_counts": {}})
            bucket["weighted_sum"] += SENTIMENT_SCORES[label] * count
            bucket["total"] += count
            bucket["label_counts"][label.value] = count

        return [
            SentimentTrendPoint(
                date=day,
                average_score=bucket["weighted_sum"] / bucket["total"],
                label_counts=bucket["label_counts"],
            )
            for day, bucket in by_day.items()
        ]
