import pytest

from backend.services.anomaly_service.app.services.aggregators.region_aggregator import RegionAggregator
from backend.services.anomaly_service.app.utils.time_window import resolve_window


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    async def count_complaints_by_region(self, start, end):
        return self.rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_no_complaints_returns_empty_list():
    aggregator = RegionAggregator(FakeRepository([]))
    points = await aggregator.aggregate(resolve_window(30))
    assert points == []


@pytest.mark.anyio
async def test_single_region_produces_single_point():
    aggregator = RegionAggregator(FakeRepository([("North", 1)]))
    points = await aggregator.aggregate(resolve_window(30))
    assert len(points) == 1
    assert points[0].region == "North"
    assert points[0].count == 1


@pytest.mark.anyio
async def test_mixed_regions_are_all_present():
    rows = [("North", 12), ("South", 7), ("unknown", 3)]
    aggregator = RegionAggregator(FakeRepository(rows))
    points = await aggregator.aggregate(resolve_window(30))
    regions = {p.region: p.count for p in points}
    assert regions == {"North": 12, "South": 7, "unknown": 3}
