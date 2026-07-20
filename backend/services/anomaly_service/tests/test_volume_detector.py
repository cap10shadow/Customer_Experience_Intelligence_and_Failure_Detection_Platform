import pytest

from backend.services.anomaly_service.app.services.detectors.volume_detector import VolumeDetector
from backend.services.anomaly_service.app.utils.time_window import resolve_comparison_windows
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType


class FakeRepository:
    """Returns `current_rows` on the first call, `previous_rows` on the second —
    matching the detector's own call order (current window, then previous)."""

    def __init__(self, current_rows, previous_rows):
        self._responses = [current_rows, previous_rows]
        self._call_index = 0

    async def count_complaints_by_day(self, start, end):
        rows = self._responses[self._call_index]
        self._call_index += 1
        return rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_week1_10_week2_12_is_no_anomaly():
    current, previous = resolve_comparison_windows(7)
    detector = VolumeDetector(FakeRepository(current_rows=[("d", 12)], previous_rows=[("d", 10)]))
    candidates = await detector.detect(current, previous)
    assert candidates == []


@pytest.mark.anyio
async def test_week1_10_week2_30_is_a_volume_anomaly():
    current, previous = resolve_comparison_windows(7)
    detector = VolumeDetector(FakeRepository(current_rows=[("d", 30)], previous_rows=[("d", 10)]))
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.type == AnomalyType.COMPLAINT_SPIKE
    assert candidate.entity_type == "global"
    assert candidate.entity_value is None
    assert candidate.baseline_value == 10
    assert candidate.current_value == 30
    assert candidate.percentage_change == 200.0
    assert candidate.severity == AnomalySeverity.HIGH
    assert candidate.triggered_rule
    assert candidate.explanation


@pytest.mark.anyio
async def test_no_complaints_in_either_window_is_no_anomaly():
    current, previous = resolve_comparison_windows(7)
    detector = VolumeDetector(FakeRepository(current_rows=[], previous_rows=[]))
    candidates = await detector.detect(current, previous)
    assert candidates == []


@pytest.mark.anyio
async def test_decrease_is_not_flagged():
    current, previous = resolve_comparison_windows(7)
    detector = VolumeDetector(FakeRepository(current_rows=[("d", 5)], previous_rows=[("d", 50)]))
    candidates = await detector.detect(current, previous)
    assert candidates == []


@pytest.mark.anyio
async def test_multi_day_rows_are_summed():
    current, previous = resolve_comparison_windows(7)
    detector = VolumeDetector(
        FakeRepository(current_rows=[("d1", 15), ("d2", 15)], previous_rows=[("d1", 5), ("d2", 5)])
    )
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    assert candidates[0].current_value == 30
    assert candidates[0].baseline_value == 10
