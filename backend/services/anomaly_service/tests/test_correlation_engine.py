import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.services.anomaly_service.app.services.correlation_engine import CorrelationEngine
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyStatus, AnomalyType
from backend.shared.constants.enums.incident import IncidentStatus


class FakeAnomalyRepository:
    """In-memory stand-in for AnomalyRepository — the Correlation Engine
    only ever reads active anomalies, never writes to this table."""

    def __init__(self, anomalies):
        self.anomalies = anomalies

    async def list_active(self):
        return [a for a in self.anomalies if a.status == AnomalyStatus.ACTIVE]


class FakeIncidentRepository:
    """In-memory stand-in for IncidentRepository, used to exercise the real
    CorrelationEngine reconciliation logic without a database."""

    def __init__(self, anomalies_by_id):
        self.anomalies_by_id = anomalies_by_id
        self.incidents = {}
        self.links = []  # (incident_id, active_anomaly_id, linked_at)

    async def create_incident(self, incident):
        incident.id = uuid.uuid4()
        self.incidents[incident.id] = incident
        return incident

    async def save(self, incident):
        return incident

    async def get_by_id(self, incident_id):
        return self.incidents.get(incident_id)

    async def list_open(self):
        return [i for i in self.incidents.values() if i.status == IncidentStatus.OPEN]

    async def get_open_incident_for_anomaly(self, active_anomaly_id):
        for incident_id, anomaly_id, _ in self.links:
            if anomaly_id == active_anomaly_id:
                incident = self.incidents.get(incident_id)
                if incident is not None and incident.status == IncidentStatus.OPEN:
                    return incident
        return None

    async def is_anomaly_linked(self, incident_id, active_anomaly_id):
        return any(l[0] == incident_id and l[1] == active_anomaly_id for l in self.links)

    async def link_anomaly(self, incident_id, active_anomaly_id, linked_at):
        self.links.append((incident_id, active_anomaly_id, linked_at))

    async def list_linked_anomalies(self, incident_id):
        ids = [aid for iid, aid, _ in self.links if iid == incident_id]
        return [self.anomalies_by_id[aid] for aid in ids if aid in self.anomalies_by_id]


def _engine(anomalies):
    anomalies_by_id = {a.id: a for a in anomalies}
    anomaly_repo = FakeAnomalyRepository(anomalies)
    incident_repo = FakeIncidentRepository(anomalies_by_id)
    return CorrelationEngine(incident_repo, anomaly_repo), incident_repo, anomaly_repo


@pytest.mark.anyio
async def test_five_related_anomalies_within_ten_minutes_form_one_incident(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, entity_type="global", severity=AnomalySeverity.CRITICAL, first_detected_at=base),
        make_anomaly(type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="payment_issue", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=2)),
        make_anomaly(type=AnomalyType.REGIONAL_SPIKE, entity_type="region", entity_value="South", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=4)),
        make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=6)),
        make_anomaly(type=AnomalyType.SENTIMENT_SHIFT, entity_type="global", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=8)),
    ]
    engine, incident_repo, _ = _engine(anomalies)

    result = await engine.run(window_minutes=15)

    assert len(result.created) == 1
    assert result.created[0].linked_anomaly_count == 5
    assert len(incident_repo.incidents) == 1

    incident = list(incident_repo.incidents.values())[0]
    assert incident.status == IncidentStatus.OPEN
    # timing (+20) + severity (+15) + supporting signals (+20) = 55 -> "Possible"
    assert incident.confidence_score == 55


@pytest.mark.anyio
async def test_distant_regions_form_separate_incidents(make_anomaly):
    today = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    three_weeks_ago = today - timedelta(weeks=3)

    south_cluster = [
        make_anomaly(type=AnomalyType.REGIONAL_SPIKE, entity_type="region", entity_value="South", severity=AnomalySeverity.HIGH, first_detected_at=today),
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, entity_type="global", severity=AnomalySeverity.HIGH, first_detected_at=today + timedelta(minutes=3)),
    ]
    north_cluster = [
        make_anomaly(type=AnomalyType.REGIONAL_SPIKE, entity_type="region", entity_value="North", severity=AnomalySeverity.HIGH, first_detected_at=three_weeks_ago),
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, entity_type="global", severity=AnomalySeverity.HIGH, first_detected_at=three_weeks_ago + timedelta(minutes=3)),
    ]
    engine, incident_repo, _ = _engine(south_cluster + north_cluster)

    result = await engine.run(window_minutes=15)

    assert len(result.created) == 2
    titles = {item.incident.title for item in result.created}
    assert "South Regional Incident" in titles
    assert "North Regional Incident" in titles


@pytest.mark.anyio
async def test_single_anomaly_never_forms_an_incident(make_anomaly):
    engine, incident_repo, _ = _engine([make_anomaly()])
    result = await engine.run(window_minutes=15)
    assert result.created == []
    assert incident_repo.incidents == {}


@pytest.mark.anyio
async def test_low_confidence_cluster_does_not_form_an_incident(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    # Two anomalies, close in time, but differing severity and no supporting
    # signal pairing -> only the timing rule fires (20 points, "Weak" tier).
    anomalies = [
        make_anomaly(type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="payment_issue", severity=AnomalySeverity.LOW, first_detected_at=base),
        make_anomaly(type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="delivery_issue", severity=AnomalySeverity.HIGH, first_detected_at=base + timedelta(minutes=1)),
    ]
    engine, incident_repo, _ = _engine(anomalies)

    result = await engine.run(window_minutes=15)

    assert result.created == []
    assert incident_repo.incidents == {}


@pytest.mark.anyio
async def test_duplicate_prevention_no_new_incident_or_links_on_rerun(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, severity=AnomalySeverity.CRITICAL, first_detected_at=base),
        make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=1)),
    ]
    engine, incident_repo, _ = _engine(anomalies)

    first = await engine.run(window_minutes=15)
    second = await engine.run(window_minutes=15)

    assert len(first.created) == 1
    assert second.created == []
    assert second.updated == []  # reconfirmed, but nothing meaningful changed
    assert len(incident_repo.incidents) == 1
    assert len(incident_repo.links) == 2  # no duplicate link rows


@pytest.mark.anyio
async def test_new_anomaly_joining_cluster_updates_existing_incident(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    a1 = make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, severity=AnomalySeverity.CRITICAL, first_detected_at=base)
    a2 = make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=1))
    anomalies = [a1, a2]
    engine, incident_repo, anomaly_repo = _engine(anomalies)

    first = await engine.run(window_minutes=15)
    incident_id = first.created[0].incident.id

    # A third, related anomaly appears just after the first run.
    a3 = make_anomaly(type=AnomalyType.SENTIMENT_SHIFT, severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=2))
    anomalies.append(a3)
    incident_repo.anomalies_by_id[a3.id] = a3

    second = await engine.run(window_minutes=15)

    assert second.created == []
    assert len(second.updated) == 1
    assert second.updated[0].incident.id == incident_id
    assert second.updated[0].linked_anomaly_count == 3
    assert len(incident_repo.links) == 3


@pytest.mark.anyio
async def test_incident_resolves_when_all_linked_anomalies_resolve(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    a1 = make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, severity=AnomalySeverity.CRITICAL, first_detected_at=base)
    a2 = make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=1))
    anomalies = [a1, a2]
    engine, incident_repo, _ = _engine(anomalies)

    first = await engine.run(window_minutes=15)
    incident_id = first.created[0].incident.id

    a1.status = AnomalyStatus.RESOLVED
    a2.status = AnomalyStatus.RESOLVED

    second = await engine.run(window_minutes=15)

    assert len(second.resolved) == 1
    assert second.resolved[0].incident.id == incident_id
    assert incident_repo.incidents[incident_id].status == IncidentStatus.RESOLVED
    assert incident_repo.incidents[incident_id].resolved_at is not None


@pytest.mark.anyio
async def test_incident_not_resolved_while_any_linked_anomaly_still_active(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    a1 = make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, severity=AnomalySeverity.CRITICAL, first_detected_at=base)
    a2 = make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=1))
    anomalies = [a1, a2]
    engine, incident_repo, _ = _engine(anomalies)

    first = await engine.run(window_minutes=15)
    incident_id = first.created[0].incident.id

    a1.status = AnomalyStatus.RESOLVED  # only one of the two resolves

    second = await engine.run(window_minutes=15)

    assert second.resolved == []
    assert incident_repo.incidents[incident_id].status == IncidentStatus.OPEN


@pytest.mark.anyio
async def test_get_active_and_get_by_id(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, severity=AnomalySeverity.CRITICAL, first_detected_at=base),
        make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=1)),
    ]
    engine, _, _ = _engine(anomalies)

    result = await engine.run(window_minutes=15)
    incident_id = result.created[0].incident.id

    active = await engine.get_active()
    assert len(active) == 1
    assert active[0].id == incident_id

    fetched = await engine.get_by_id(incident_id)
    assert fetched is not None
    assert fetched.id == incident_id

    assert await engine.get_by_id(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_get_anomalies_for_incident(make_anomaly):
    base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    anomalies = [
        make_anomaly(type=AnomalyType.COMPLAINT_SPIKE, severity=AnomalySeverity.CRITICAL, first_detected_at=base),
        make_anomaly(type=AnomalyType.URGENCY_SPIKE, entity_type="urgency", entity_value="critical", severity=AnomalySeverity.CRITICAL, first_detected_at=base + timedelta(minutes=1)),
    ]
    engine, _, _ = _engine(anomalies)

    result = await engine.run(window_minutes=15)
    incident_id = result.created[0].incident.id

    linked = await engine.get_anomalies_for_incident(incident_id)
    assert len(linked) == 2

    assert await engine.get_anomalies_for_incident(uuid.uuid4()) is None
