import pytest

from backend.services.anomaly_service.app.services.aggregators.category_aggregator import CategoryAggregator
from backend.services.anomaly_service.app.utils.time_window import resolve_window
from backend.shared.constants.enums.complaint import IssueCategory


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    async def count_enrichments_by_category(self, start, end):
        return self.rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_no_enrichments_returns_empty_list():
    aggregator = CategoryAggregator(FakeRepository([]))
    points = await aggregator.aggregate(resolve_window(30))
    assert points == []


@pytest.mark.anyio
async def test_single_category_produces_single_point():
    aggregator = CategoryAggregator(FakeRepository([(IssueCategory.DELIVERY_ISSUE, 1)]))
    points = await aggregator.aggregate(resolve_window(30))
    assert len(points) == 1
    assert points[0].category == "delivery_issue"
    assert points[0].count == 1


@pytest.mark.anyio
async def test_mixed_categories_are_all_present():
    rows = [
        (IssueCategory.DELIVERY_ISSUE, 10),
        (IssueCategory.PAYMENT_ISSUE, 5),
        (IssueCategory.ACCOUNT_ISSUE, 2),
    ]
    aggregator = CategoryAggregator(FakeRepository(rows))
    points = await aggregator.aggregate(resolve_window(30))
    categories = {p.category: p.count for p in points}
    assert categories == {"delivery_issue": 10, "payment_issue": 5, "account_issue": 2}
