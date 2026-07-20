import pytest

from backend.services.anomaly_service.app.services.detectors.category_detector import CategoryDetector
from backend.services.anomaly_service.app.utils.time_window import resolve_comparison_windows
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory


class FakeRepository:
    def __init__(self, current_rows, previous_rows):
        self._responses = [current_rows, previous_rows]
        self._call_index = 0

    async def count_enrichments_by_category(self, start, end):
        rows = self._responses[self._call_index]
        self._call_index += 1
        return rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_billing_8_to_28_is_a_category_anomaly():
    current, previous = resolve_comparison_windows(30)
    detector = CategoryDetector(
        FakeRepository(
            current_rows=[(IssueCategory.PAYMENT_ISSUE, 28)],
            previous_rows=[(IssueCategory.PAYMENT_ISSUE, 8)],
        )
    )
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.type == AnomalyType.CATEGORY_SPIKE
    assert candidate.entity_type == "category"
    assert candidate.entity_value == "payment_issue"
    assert candidate.baseline_value == 8
    assert candidate.current_value == 28
    assert candidate.percentage_change == 250.0
    assert candidate.severity == AnomalySeverity.CRITICAL


@pytest.mark.anyio
async def test_only_anomalous_categories_are_returned():
    current, previous = resolve_comparison_windows(30)
    detector = CategoryDetector(
        FakeRepository(
            current_rows=[(IssueCategory.PAYMENT_ISSUE, 28), (IssueCategory.DELIVERY_ISSUE, 11)],
            previous_rows=[(IssueCategory.PAYMENT_ISSUE, 8), (IssueCategory.DELIVERY_ISSUE, 10)],
        )
    )
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    assert candidates[0].entity_value == "payment_issue"


@pytest.mark.anyio
async def test_category_missing_from_previous_window_treated_as_zero_baseline():
    current, previous = resolve_comparison_windows(30)
    detector = CategoryDetector(
        FakeRepository(
            current_rows=[(IssueCategory.ACCOUNT_ISSUE, 5)],
            previous_rows=[],
        )
    )
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    assert candidates[0].severity == AnomalySeverity.CRITICAL
    assert candidates[0].percentage_change is None


@pytest.mark.anyio
async def test_no_data_in_either_window_is_no_anomaly():
    current, previous = resolve_comparison_windows(30)
    detector = CategoryDetector(FakeRepository(current_rows=[], previous_rows=[]))
    candidates = await detector.detect(current, previous)
    assert candidates == []
