import pytest

from backend.services.anomaly_service.app.services.detectors.region_detector import RegionDetector
from backend.services.anomaly_service.app.utils.time_window import resolve_comparison_windows
from backend.shared.constants.enums.anomaly import AnomalyType


class FakeRepository:
    def __init__(self, current_rows, previous_rows):
        self._responses = [current_rows, previous_rows]
        self._call_index = 0

    async def count_complaints_by_region(self, start, end):
        rows = self._responses[self._call_index]
        self._call_index += 1
        return rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_region_spike_detected():
    current, previous = resolve_comparison_windows(30)
    detector = RegionDetector(
        FakeRepository(current_rows=[("North", 40)], previous_rows=[("North", 10)])
    )
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.type == AnomalyType.REGIONAL_SPIKE
    assert candidate.entity_type == "region"
    assert candidate.entity_value == "North"
    assert candidate.percentage_change == 300.0


@pytest.mark.anyio
async def test_stable_region_is_not_flagged():
    current, previous = resolve_comparison_windows(30)
    detector = RegionDetector(
        FakeRepository(current_rows=[("South", 21)], previous_rows=[("South", 20)])
    )
    candidates = await detector.detect(current, previous)
    assert candidates == []


@pytest.mark.anyio
async def test_no_data_is_no_anomaly():
    current, previous = resolve_comparison_windows(30)
    detector = RegionDetector(FakeRepository(current_rows=[], previous_rows=[]))
    candidates = await detector.detect(current, previous)
    assert candidates == []
