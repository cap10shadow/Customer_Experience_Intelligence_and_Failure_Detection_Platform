import uuid

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
DatasetIdParam = Query(..., description="The Dataset these trends are scoped to.")


@router.get("", response_model=TrendSummaryResponse)
async def get_trend_summary(
    dataset_id: uuid.UUID = DatasetIdParam,
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns the overall descriptive trend summary across all metrics, for one dataset."""
    return await engine.get_summary(days, dataset_id)


@router.get("/daily", response_model=VolumeTrendResponse)
async def get_daily_volume(
    dataset_id: uuid.UUID = DatasetIdParam,
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns complaint volume over time for one dataset."""
    return await engine.get_volume_trend(days, dataset_id)


@router.get("/categories", response_model=CategoryTrendResponse)
async def get_category_trends(
    dataset_id: uuid.UUID = DatasetIdParam,
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns complaint counts grouped by detected issue category, for one dataset."""
    return await engine.get_category_trend(days, dataset_id)


@router.get("/regions", response_model=RegionTrendResponse)
async def get_region_trends(
    dataset_id: uuid.UUID = DatasetIdParam,
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns complaint counts grouped by customer region, for one dataset."""
    return await engine.get_region_trend(days, dataset_id)


@router.get("/sentiment", response_model=SentimentTrendResponse)
async def get_sentiment_trends(
    dataset_id: uuid.UUID = DatasetIdParam,
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns average sentiment over time from existing enrichment records, for one dataset."""
    return await engine.get_sentiment_trend(days, dataset_id)


@router.get("/urgency", response_model=UrgencyTrendResponse)
async def get_urgency_trends(
    dataset_id: uuid.UUID = DatasetIdParam,
    days: int = DaysParam,
    engine: TrendEngine = Depends(get_trend_engine),
):
    """Returns urgency distribution across existing enrichment records, for one dataset."""
    return await engine.get_urgency_trend(days, dataset_id)
