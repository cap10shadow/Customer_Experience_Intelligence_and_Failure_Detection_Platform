from typing import List

from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.schemas.trends import VolumeTrendPoint
from backend.services.anomaly_service.app.utils.time_window import TrendWindow


class VolumeAggregator:
    """Computes complaint volume over time. Descriptive only — no thresholds, no alerts."""

    def __init__(self, repository: TrendRepository) -> None:
        self.repository = repository

    async def aggregate(self, window: TrendWindow) -> List[VolumeTrendPoint]:
        rows = await self.repository.count_complaints_by_day(window.start, window.end)
        return [VolumeTrendPoint(date=day, count=count) for day, count in rows]
