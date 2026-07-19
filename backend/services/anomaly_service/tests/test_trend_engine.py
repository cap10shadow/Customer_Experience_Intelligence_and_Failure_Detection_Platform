from datetime import date

import pytest

from backend.services.anomaly_service.app.services.trend_engine import TrendEngine
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel


class FakeTrendRepository:
    """In-memory stand-in for TrendRepository, used to exercise the real
    TrendEngine orchestration logic without a database."""

    async def count_complaints_by_day(self, start, end):
        return [(date(2026, 7, 1), 3), (date(2026, 7, 2), 5)]

    async def count_complaints_by_region(self, start, end):
        return [("North", 4), ("South", 4)]

    async def count_enrichments_by_category(self, start, end):
        return [(IssueCategory.DELIVERY_ISSUE, 6), (IssueCategory.PAYMENT_ISSUE, 2)]

    async def count_enrichments_by_urgency(self, start, end):
        return [(UrgencyLabel.HIGH, 3), (UrgencyLabel.LOW, 5)]

    async def count_enrichments_by_day_and_sentiment(self, start, end):
        return [(date(2026, 7, 1), SentimentLabel.NEGATIVE, 8)]


@pytest.fixture
def engine():
    return TrendEngine(FakeTrendRepository())


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_get_summary_combines_every_aggregator(engine):
    summary = await engine.get_summary(30)

    assert summary.period == "Last 30 Days"
    assert len(summary.complaint_volume) == 2
    assert len(summary.categories) == 2
    assert len(summary.regions) == 2
    assert len(summary.sentiment) == 1
    assert len(summary.urgency) == 2


@pytest.mark.anyio
async def test_get_volume_trend_uses_requested_window_label(engine):
    response = await engine.get_volume_trend(7)
    assert response.period == "Last 7 Days"
    assert [p.count for p in response.complaint_volume] == [3, 5]


@pytest.mark.anyio
async def test_get_category_trend(engine):
    response = await engine.get_category_trend(90)
    assert response.period == "Last 90 Days"
    assert {p.category for p in response.categories} == {"delivery_issue", "payment_issue"}


@pytest.mark.anyio
async def test_get_region_trend(engine):
    response = await engine.get_region_trend(30)
    assert {p.region for p in response.regions} == {"North", "South"}


@pytest.mark.anyio
async def test_get_sentiment_trend(engine):
    response = await engine.get_sentiment_trend(30)
    assert response.sentiment[0].average_score == -1


@pytest.mark.anyio
async def test_get_urgency_trend(engine):
    response = await engine.get_urgency_trend(30)
    assert {p.urgency for p in response.urgency} == {"high", "low"}
