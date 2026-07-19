from datetime import date

import pytest

from backend.services.anomaly_service.app.services.aggregators.sentiment_aggregator import SentimentAggregator
from backend.services.anomaly_service.app.utils.time_window import resolve_window
from backend.shared.constants.enums.complaint import SentimentLabel


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    async def count_enrichments_by_day_and_sentiment(self, start, end):
        return self.rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_no_enrichments_returns_empty_list():
    aggregator = SentimentAggregator(FakeRepository([]))
    points = await aggregator.aggregate(resolve_window(30))
    assert points == []


@pytest.mark.anyio
async def test_single_enrichment_produces_matching_average():
    rows = [(date(2026, 7, 1), SentimentLabel.NEGATIVE, 1)]
    aggregator = SentimentAggregator(FakeRepository(rows))
    points = await aggregator.aggregate(resolve_window(30))
    assert len(points) == 1
    assert points[0].date == date(2026, 7, 1)
    assert points[0].average_score == -1
    assert points[0].label_counts == {"negative": 1}


@pytest.mark.anyio
async def test_mixed_sentiment_computes_weighted_average():
    # Day 1: 2 highly_negative (-2) + 2 positive (+1) -> weighted avg = (-4 + 2) / 4 = -0.5
    rows = [
        (date(2026, 7, 1), SentimentLabel.HIGHLY_NEGATIVE, 2),
        (date(2026, 7, 1), SentimentLabel.POSITIVE, 2),
    ]
    aggregator = SentimentAggregator(FakeRepository(rows))
    points = await aggregator.aggregate(resolve_window(30))
    assert len(points) == 1
    assert points[0].average_score == -0.5
    assert points[0].label_counts == {"highly_negative": 2, "positive": 2}


@pytest.mark.anyio
async def test_multiple_days_are_kept_separate():
    rows = [
        (date(2026, 7, 1), SentimentLabel.NEUTRAL, 3),
        (date(2026, 7, 2), SentimentLabel.POSITIVE, 5),
    ]
    aggregator = SentimentAggregator(FakeRepository(rows))
    points = await aggregator.aggregate(resolve_window(30))
    assert len(points) == 2
    assert points[0].date == date(2026, 7, 1)
    assert points[0].average_score == 0
    assert points[1].date == date(2026, 7, 2)
    assert points[1].average_score == 1
