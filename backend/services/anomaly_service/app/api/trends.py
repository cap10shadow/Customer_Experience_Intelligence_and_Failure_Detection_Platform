from fastapi import APIRouter, Depends, Query

from backend.services.anomaly_service.app.dependencies.services import get_trend_engine
from backend.services.anomaly_service.app.services.trend_engine import TrendEngine
from backend.services.anomaly_service.app.schemas.trends import (
    CategoryTrendResponse,
    RegionTrendResponse,
    SentimentTrendResponse,
    TrendSummaryResponse,
    UrgencyTrendResponse,
    VolumeTrendResponse,
)

router = APIRouter(prefix="/trends", tags=["trends"])

DaysParam = Query(30, ge=1, le=365, description="Size of the trailing time window, in days.")


@router.get("", response_model=TrendSummaryResponse)
async def get_trend_summary(
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns the overall descriptive trend summary across all metrics."""
    return await engine.get_summary(days)


@router.get("/daily", response_model=VolumeTrendResponse)
async def get_daily_volume(
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns complaint volume over time."""
    return await engine.get_volume_trend(days)


@router.get("/categories", response_model=CategoryTrendResponse)
async def get_category_trends(
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns complaint counts grouped by detected issue category."""
    return await engine.get_category_trend(days)


@router.get("/regions", response_model=RegionTrendResponse)
async def get_region_trends(
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns complaint counts grouped by customer region."""
    return await engine.get_region_trend(days)


@router.get("/sentiment", response_model=SentimentTrendResponse)
async def get_sentiment_trends(
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns average sentiment over time from existing enrichment records."""
    return await engine.get_sentiment_trend(days)


@router.get("/urgency", response_model=UrgencyTrendResponse)
async def get_urgency_trends(
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns urgency distribution across existing enrichment records."""
    return await engine.get_urgency_trend(days)
