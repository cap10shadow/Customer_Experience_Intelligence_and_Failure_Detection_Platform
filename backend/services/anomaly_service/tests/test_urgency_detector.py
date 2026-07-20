import pytest

from backend.services.anomaly_service.app.services.detectors.urgency_detector import UrgencyDetector
from backend.services.anomaly_service.app.utils.time_window import resolve_comparison_windows
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import UrgencyLabel


class FakeRepository:
    def __init__(self, current_rows, previous_rows):
        self._responses = [current_rows, previous_rows]
        self._call_index = 0

    async def count_enrichments_by_urgency(self, start, end):
        rows = self._responses[self._call_index]
        self._call_index += 1
        return rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_critical_2_to_15_is_an_urgency_anomaly():
    current, previous = resolve_comparison_windows(7)
    detector = UrgencyDetector(
        FakeRepository(
            current_rows=[(UrgencyLabel.CRITICAL, 15)],
            previous_rows=[(UrgencyLabel.CRITICAL, 2)],
        )
    )
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.type == AnomalyType.URGENCY_SPIKE
    assert candidate.entity_type == "urgency"
    assert candidate.entity_value == "critical"
    assert candidate.baseline_value == 2
    assert candidate.current_value == 15
    assert candidate.severity == AnomalySeverity.CRITICAL


@pytest.mark.anyio
async def test_no_data_is_no_anomaly():
    current, previous = resolve_comparison_windows(7)
    detector = UrgencyDetector(FakeRepository(current_rows=[], previous_rows=[]))
    candidates = await detector.detect(current, previous)
    assert candidates == []
