import uuid
from typing import List

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.schemas.trends import RegionTrendPoint
from backend.services.anomaly_service.app.utils.time_window import TrendWindow


class RegionAggregator:
    """Computes complaint counts grouped by customer region."""

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def aggregate(self, window: TrendWindow, dataset_id: uuid.UUID) -> List[RegionTrendPoint]:
        rows = await self.repository.count_complaints_by_region(window.start, window.end, dataset_id)
        return [RegionTrendPoint(region=region, count=count) for region, count in rows]
