from datetime import date

import pytest

from backend.services.anomaly_service.app.services.detectors.sentiment_detector import SentimentDetector
from backend.services.anomaly_service.app.utils.time_window import resolve_comparison_windows
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import SentimentLabel


class FakeRepository:
    def __init__(self, current_rows, previous_rows):
        self._responses = [current_rows, previous_rows]
        self._call_index = 0

    async def count_enrichments_by_day_and_sentiment(self, start, end):
        rows = self._responses[self._call_index]
        self._call_index += 1
        return rows


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_positive_to_highly_negative_is_a_sentiment_anomaly():
    current, previous = resolve_comparison_windows(7)
    detector = SentimentDetector(
        FakeRepository(
            current_rows=[(date(2026, 7, 1), SentimentLabel.HIGHLY_NEGATIVE, 10)],
            previous_rows=[(date(2026, 6, 24), SentimentLabel.POSITIVE, 10)],
        )
    )
    candidates = await detector.detect(current, previous)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.type == AnomalyType.SENTIMENT_SHIFT
    assert candidate.entity_type == "global"
    assert candidate.baseline_value == 1
    assert candidate.current_value == -2
    assert candidate.percentage_change == -300.0
    assert candidate.severity == AnomalySeverity.CRITICAL


@pytest.mark.anyio
async def test_improving_sentiment_is_not_flagged():
    current, previous = resolve_comparison_windows(7)
    detector = SentimentDetector(
        FakeRepository(
            current_rows=[(date(2026, 7, 1), SentimentLabel.POSITIVE, 10)],
            previous_rows=[(date(2026, 6, 24), SentimentLabel.HIGHLY_NEGATIVE, 10)],
        )
    )
    candidates = await detector.detect(current, previous)
    assert candidates == []


@pytest.mark.anyio
async def test_no_data_in_a_window_is_not_flagged():
    current, previous = resolve_comparison_windows(7)
    detector = SentimentDetector(
        FakeRepository(
            current_rows=[(date(2026, 7, 1), SentimentLabel.HIGHLY_NEGATIVE, 10)],
            previous_rows=[],
        )
    )
    candidates = await detector.detect(current, previous)
    assert candidates == []


@pytest.mark.anyio
async def test_stable_sentiment_is_not_flagged():
    current, previous = resolve_comparison_windows(7)
    detector = SentimentDetector(
        FakeRepository(
            current_rows=[(date(2026, 7, 1), SentimentLabel.NEUTRAL, 10)],
            previous_rows=[(date(2026, 6, 24), SentimentLabel.NEUTRAL, 10)],
        )
    )
    candidates = await detector.detect(current, previous)
    assert candidates == []
