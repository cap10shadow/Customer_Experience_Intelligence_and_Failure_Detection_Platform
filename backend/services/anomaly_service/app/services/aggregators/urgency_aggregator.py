from typing import List

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.schemas.trends import UrgencyTrendPoint
from backend.services.anomaly_service.app.utils.time_window import TrendWindow


class UrgencyAggregator:
    """Computes complaint counts grouped by urgency level."""

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def aggregate(self, window: TrendWindow) -> List[UrgencyTrendPoint]:
        rows = await self.repository.count_enrichments_by_urgency(window.start, window.end)
        return [UrgencyTrendPoint(urgency=urgency.value, count=count) for urgency, count in rows]
