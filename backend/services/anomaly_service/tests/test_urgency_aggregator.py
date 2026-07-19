import pytest

from backend.services.anomaly_service.app.services.aggregators.urgency_aggregator import UrgencyAggregator
from backend.services.anomaly_service.app.utils.time_window import resolve_window
from backend.shared.constants.enums.complaint import UrgencyLabel


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    async def count_enrichments_by_urgency(self, start, end):
        return self.rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_no_enrichments_returns_empty_list():
    aggregator = UrgencyAggregator(FakeRepository([]))
    points = await aggregator.aggregate(resolve_window(30))
    assert points == []


@pytest.mark.anyio
async def test_single_urgency_produces_single_point():
    aggregator = UrgencyAggregator(FakeRepository([(UrgencyLabel.CRITICAL, 1)]))
    points = await aggregator.aggregate(resolve_window(30))
    assert len(points) == 1
    assert points[0].urgency == "critical"
    assert points[0].count == 1


@pytest.mark.anyio
async def test_full_urgency_distribution():
    rows = [
        (UrgencyLabel.LOW, 4),
        (UrgencyLabel.MEDIUM, 6),
        (UrgencyLabel.HIGH, 3),
        (UrgencyLabel.CRITICAL, 1),
    ]
    aggregator = UrgencyAggregator(FakeRepository(rows))
    points = await aggregator.aggregate(resolve_window(30))
    urgency = {p.urgency: p.count for p in points}
    assert urgency == {"low": 4, "medium": 6, "high": 3, "critical": 1}
