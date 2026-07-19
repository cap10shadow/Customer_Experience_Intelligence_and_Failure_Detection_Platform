from datetime import date

import pytest

from backend.services.anomaly_service.app.services.aggregators.volume_aggregator import VolumeAggregator
from backend.services.anomaly_service.app.utils.time_window import resolve_window


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    async def count_complaints_by_day(self, start, end):
        return self.rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_no_complaints_returns_empty_list():
    aggregator = VolumeAggregator(FakeRepository([]))
    points = await aggregator.aggregate(resolve_window(30))
    assert points == []


@pytest.mark.anyio
async def test_single_complaint_produces_single_point():
    aggregator = VolumeAggregator(FakeRepository([(date(2026, 7, 1), 1)]))
    points = await aggregator.aggregate(resolve_window(30))
    assert len(points) == 1
    assert points[0].date == date(2026, 7, 1)
    assert points[0].count == 1


@pytest.mark.anyio
async def test_large_dataset_preserves_all_points():
    rows = [(date(2026, 1, 1 + i % 28), i + 1) for i in range(90)]
    aggregator = VolumeAggregator(FakeRepository(rows))
    points = await aggregator.aggregate(resolve_window(90))
    assert len(points) == 90
    assert points[-1].count == 90
