from typing import List

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.schemas.trends import CategoryTrendPoint
from backend.services.anomaly_service.app.utils.time_window import TrendWindow


class CategoryAggregator:
    """
    Computes complaint counts grouped by detected issue category.

    Reuses the issue category already classified by the NLP service's
    enrichment pipeline — this aggregator does not perform any classification
    of its own.
    """

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def aggregate(self, window: TrendWindow) -> List[CategoryTrendPoint]:
        rows = await self.repository.count_enrichments_by_category(window.start, window.end)
        return [CategoryTrendPoint(category=category.value, count=count) for category, count in rows]
