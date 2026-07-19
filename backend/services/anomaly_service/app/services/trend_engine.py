from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.schemas.trends import (
    CategoryTrendResponse,
    RegionTrendResponse,
    SentimentTrendResponse,
    TrendSummaryResponse,
    UrgencyTrendResponse,
    VolumeTrendResponse,
)
from backend.services.anomaly_service.app.services.aggregators.category_aggregator import CategoryAggregator
from backend.services.anomaly_service.app.services.aggregators.region_aggregator import RegionAggregator
from backend.services.anomaly_service.app.services.aggregators.sentiment_aggregator import SentimentAggregator
from backend.services.anomaly_service.app.services.aggregators.urgency_aggregator import UrgencyAggregator
from backend.services.anomaly_service.app.services.aggregators.volume_aggregator import VolumeAggregator
from backend.services.anomaly_service.app.utils.time_window import resolve_window


class TrendEngine:
    """
    Trend Analysis Engine

    Ownership:
    Owned by the Anomaly Service.

    Operational Purpose:
    Orchestrates the descriptive-analytics aggregators, turning historical
    complaint and complaint-enrichment data into structured trend metrics.

    Philosophy:
    - Descriptive only: no anomaly detection, severity, or persistence.
    - Read-only: computes trends dynamically on every call, no caching table.
    - Sequential by construction: every aggregator shares one AsyncSession via
      the repository, so calls are awaited one at a time rather than via
      asyncio.gather (concurrent use of a single AsyncSession is unsupported).
    """

    def __init__(self, repository: TrendRepository) -> None:
        self.volume = VolumeAggregator(repository)
        self.categories = CategoryAggregator(repository)
        self.regions = RegionAggregator(repository)
        self.sentiment = SentimentAggregator(repository)
        self.urgency = UrgencyAggregator(repository)

    async def get_volume_trend(self, days: int) -> VolumeTrendResponse:
        window = resolve_window(days)
        points = await self.volume.aggregate(window)
        return VolumeTrendResponse(period=window.label, complaint_volume=points)

    async def get_category_trend(self, days: int) -> CategoryTrendResponse:
        window = resolve_window(days)
        points = await self.categories.aggregate(window)
        return CategoryTrendResponse(period=window.label, categories=points)

    async def get_region_trend(self, days: int) -> RegionTrendResponse:
        window = resolve_window(days)
        points = await self.regions.aggregate(window)
        return RegionTrendResponse(period=window.label, regions=points)

    async def get_sentiment_trend(self, days: int) -> SentimentTrendResponse:
        window = resolve_window(days)
        points = await self.sentiment.aggregate(window)
        return SentimentTrendResponse(period=window.label, sentiment=points)

    async def get_urgency_trend(self, days: int) -> UrgencyTrendResponse:
        window = resolve_window(days)
        points = await self.urgency.aggregate(window)
        return UrgencyTrendResponse(period=window.label, urgency=points)

    async def get_summary(self, days: int) -> TrendSummaryResponse:
        window = resolve_window(days)

        volume_points = await self.volume.aggregate(window)
        category_points = await self.categories.aggregate(window)
        region_points = await self.regions.aggregate(window)
        sentiment_points = await self.sentiment.aggregate(window)
        urgency_points = await self.urgency.aggregate(window)

        return TrendSummaryResponse(
            period=window.label,
            complaint_volume=volume_points,
            categories=category_points,
            regions=region_points,
            sentiment=sentiment_points,
            urgency=urgency_points,
        )
