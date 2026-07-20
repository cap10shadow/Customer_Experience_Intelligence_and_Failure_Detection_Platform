import uuid

import pytest

from backend.services.anomaly_service.app.services.anomaly_engine import AnomalyEngine
from backend.shared.constants.enums.anomaly import AnomalyEventType, AnomalySeverity, AnomalyStatus


class FakeTrendRepository:
    """
    Serves canned rows to the 5 detectors. Each dimension is a list of
    responses consumed in call order (current window, then previous window,
    per `run()` invocation) — so a test driving N runs supplies 2*N entries.
    Dimensions not configured default to "no data", so only the detector(s)
    under test actually produce a candidate.
    """

    def __init__(self, *, volume=None, regions=None, categories=None, urgencies=None, sentiment=None):
        self._volume = list(volume or [])
        self._regions = list(regions or [])
        self._categories = list(categories or [])
        self._urgencies = list(urgencies or [])
        self._sentiment = list(sentiment or [])

    async def count_complaints_by_day(self, start, end):
        return self._volume.pop(0) if self._volume else []

    async def count_complaints_by_region(self, start, end):
        return self._regions.pop(0) if self._regions else []

    async def count_enrichments_by_category(self, start, end):
        return self._categories.pop(0) if self._categories else []

    async def count_enrichments_by_urgency(self, start, end):
        return self._urgencies.pop(0) if self._urgencies else []

    async def count_enrichments_by_day_and_sentiment(self, start, end):
        return self._sentiment.pop(0) if self._sentiment else []


class FakeAnomalyRepository:
    """In-memory stand-in for AnomalyRepository, used to exercise the real
    AnomalyEngine reconciliation logic without a database."""

    def __init__(self):
        self.by_fingerprint = {}
        self.by_id = {}
        self.history = []

    async def get_active_by_fingerprint(self, fingerprint):
        return self.by_fingerprint.get(fingerprint)

    async def get_by_id(self, anomaly_id):
        return self.by_id.get(anomaly_id)

    async def create_active(self, anomaly):
        anomaly.id = uuid.uuid4()
        self.by_fingerprint[anomaly.fingerprint] = anomaly
        self.by_id[anomaly.id] = anomaly
        return anomaly

    async def save(self, anomaly):
        return anomaly

    async def list_active(self, status=AnomalyStatus.ACTIVE):
        return [a for a in self.by_fingerprint.values() if a.status == status]

    async def add_history_event(self, event):
        event.id = uuid.uuid4()
        self.history.append(event)
        return event

    async def get_latest_run_timestamp(self):
        timestamps = [a.last_seen_at for a in self.by_fingerprint.values()] + [e.event_timestamp for e in self.history]
        return max(timestamps) if timestamps else None

    async def list_history_at(self, timestamp):
        return [e for e in self.history if e.event_timestamp == timestamp]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_first_run_creates_active_anomaly_and_detected_history():
    anomaly_repo = FakeAnomalyRepository()
    trend_repo = FakeTrendRepository(volume=[[("d", 30)], [("d", 10)]])
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    result = await engine.run(days=7)

    assert len(result.detected) == 1
    assert result.updated == []
    assert result.resolved == []
    assert len(anomaly_repo.by_fingerprint) == 1
    assert len(anomaly_repo.history) == 1
    assert anomaly_repo.history[0].event_type == AnomalyEventType.DETECTED
    assert anomaly_repo.history[0].old_severity is None


@pytest.mark.anyio
async def test_fingerprint_matching_reuses_same_row_across_runs():
    anomaly_repo = FakeAnomalyRepository()
    trend_repo = FakeTrendRepository(
        volume=[[("d", 30)], [("d", 10)], [("d", 31)], [("d", 10)]]
    )
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    first = await engine.run(days=7)
    second = await engine.run(days=7)

    first_id = first.detected[0].anomaly.id
    assert len(anomaly_repo.by_fingerprint) == 1  # no duplicate row created
    assert anomaly_repo.by_fingerprint[list(anomaly_repo.by_fingerprint)[0]].id == first_id
    assert second.updated[0].anomaly.id == first_id  # same row, reported via fingerprint match


@pytest.mark.anyio
async def test_duplicate_prevention_no_history_when_severity_unchanged():
    anomaly_repo = FakeAnomalyRepository()
    # Both runs produce the same ~200% change -> HIGH both times.
    trend_repo = FakeTrendRepository(
        volume=[[("d", 30)], [("d", 10)], [("d", 30)], [("d", 10)]]
    )
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    await engine.run(days=7)
    second = await engine.run(days=7)

    assert second.detected == []
    assert second.updated == []  # reconfirmed, but nothing meaningful changed
    assert len(anomaly_repo.history) == 1  # still just the original DETECTED event


@pytest.mark.anyio
async def test_severity_change_creates_updated_history():
    anomaly_repo = FakeAnomalyRepository()
    # Run 1: 10 -> 30 (200%, HIGH). Run 2: 10 -> 100 (900%, CRITICAL).
    trend_repo = FakeTrendRepository(
        volume=[[("d", 30)], [("d", 10)], [("d", 100)], [("d", 10)]]
    )
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    first = await engine.run(days=7)
    second = await engine.run(days=7)

    assert first.detected[0].anomaly.severity == AnomalySeverity.HIGH
    assert len(second.updated) == 1
    updated_anomaly = second.updated[0].anomaly
    assert updated_anomaly.severity == AnomalySeverity.CRITICAL
    assert updated_anomaly.id == first.detected[0].anomaly.id  # same fingerprint/row

    assert len(anomaly_repo.history) == 2
    assert anomaly_repo.history[1].event_type == AnomalyEventType.UPDATED
    assert anomaly_repo.history[1].old_severity == AnomalySeverity.HIGH
    assert anomaly_repo.history[1].new_severity == AnomalySeverity.CRITICAL


@pytest.mark.anyio
async def test_anomaly_no_longer_detected_is_resolved():
    anomaly_repo = FakeAnomalyRepository()
    # Run 1: spike present. Run 2: back to identical values (no data supplied -> 0/0, skipped).
    trend_repo = FakeTrendRepository(volume=[[("d", 30)], [("d", 10)], [], []])
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    first = await engine.run(days=7)
    second = await engine.run(days=7)

    assert len(first.detected) == 1
    assert len(second.resolved) == 1
    resolved_anomaly = second.resolved[0].anomaly
    assert resolved_anomaly.status == AnomalyStatus.RESOLVED
    assert resolved_anomaly.id == first.detected[0].anomaly.id

    assert len(anomaly_repo.history) == 2
    assert anomaly_repo.history[1].event_type == AnomalyEventType.RESOLVED
    assert anomaly_repo.history[1].old_severity == AnomalySeverity.HIGH
    assert anomaly_repo.history[1].new_severity is None


@pytest.mark.anyio
async def test_resolved_anomaly_reappearing_is_reactivated_not_duplicated():
    anomaly_repo = FakeAnomalyRepository()
    trend_repo = FakeTrendRepository(
        volume=[
            [("d", 30)], [("d", 10)],  # run 1: detected
            [], [],                     # run 2: resolved
            [("d", 30)], [("d", 10)],  # run 3: detected again
        ]
    )
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    first = await engine.run(days=7)
    await engine.run(days=7)
    third = await engine.run(days=7)

    assert len(anomaly_repo.by_fingerprint) == 1  # still exactly one row for this fingerprint
    assert len(third.detected) == 1
    assert third.detected[0].anomaly.id == first.detected[0].anomaly.id
    assert third.detected[0].anomaly.status == AnomalyStatus.ACTIVE

    event_types = [e.event_type for e in anomaly_repo.history]
    assert event_types == [AnomalyEventType.DETECTED, AnomalyEventType.RESOLVED, AnomalyEventType.DETECTED]


@pytest.mark.anyio
async def test_get_active_returns_only_active_status():
    anomaly_repo = FakeAnomalyRepository()
    trend_repo = FakeTrendRepository(volume=[[("d", 30)], [("d", 10)], [], []])
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    await engine.run(days=7)
    active_before = await engine.get_active()
    assert len(active_before) == 1

    await engine.run(days=7)  # resolves it
    active_after = await engine.get_active()
    assert active_after == []


@pytest.mark.anyio
async def test_get_latest_reconstructs_most_recent_run():
    anomaly_repo = FakeAnomalyRepository()
    trend_repo = FakeTrendRepository(volume=[[("d", 30)], [("d", 10)]])
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    run_result = await engine.run(days=7)
    latest = await engine.get_latest()

    assert latest.run_at == run_result.run_at
    assert len(latest.detected) == 1
    assert latest.detected[0].anomaly.id == run_result.detected[0].anomaly.id


@pytest.mark.anyio
async def test_get_latest_with_no_runs_returns_empty_result():
    anomaly_repo = FakeAnomalyRepository()
    trend_repo = FakeTrendRepository()
    engine = AnomalyEngine(anomaly_repo, trend_repo)

    latest = await engine.get_latest()

    assert latest.run_at is None
    assert latest.detected == []
    assert latest.updated == []
    assert latest.resolved == []
