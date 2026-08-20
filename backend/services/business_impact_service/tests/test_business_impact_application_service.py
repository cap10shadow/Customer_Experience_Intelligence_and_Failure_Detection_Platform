import uuid

import pytest

from backend.services.business_impact_service.app.domain.business_priority import BusinessPriority
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel
from backend.services.business_impact_service.app.repositories.incident_read_repository import (
    PersistedActiveAnomaly,
    PersistedIncident,
)
from backend.services.business_impact_service.app.repositories.root_cause_read_repository import PersistedRootCause
from backend.services.business_impact_service.app.services.business_impact_application_service import (
    BusinessImpactApplicationService,
)
from backend.services.business_impact_service.app.services.exceptions import (
    IncidentNotFoundError,
    RootCauseNotFoundError,
)
from backend.services.business_impact_service.app.services.impact_engine import BusinessImpactEngine, default_rules
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.root_cause import RootCause

DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


class FakeIncidentReadRepository:
    """In-memory stand-in for IncidentReadRepository."""

    def __init__(self, incidents_by_id):
        self._incidents_by_id = incidents_by_id

    async def get_by_id(self, incident_id):
        return self._incidents_by_id.get(incident_id)


class FakeRootCauseReadRepository:
    """In-memory stand-in for RootCauseReadRepository."""

    def __init__(self, root_causes_by_incident_id):
        self._root_causes_by_incident_id = root_causes_by_incident_id

    async def get_by_incident(self, incident_id):
        return self._root_causes_by_incident_id.get(incident_id)


class FakeBusinessImpactRepository:
    """In-memory stand-in for BusinessImpactRepository, used to exercise the
    real BusinessImpactApplicationService orchestration logic without a
    database."""

    def __init__(self):
        self.by_id = {}

    async def save(self, entity):
        entity.assessment_id = uuid.uuid4()
        self.by_id[entity.assessment_id] = entity
        return entity

    async def get(self, assessment_id):
        return self.by_id.get(assessment_id)

    async def list(self, *, severity=None, priority=None, incident_id=None, dataset_id=None, dataset_version_id=None):
        results = list(self.by_id.values())
        if severity is not None:
            results = [r for r in results if r.overall_severity == severity]
        if priority is not None:
            results = [r for r in results if r.business_priority == priority]
        if incident_id is not None:
            results = [r for r in results if r.incident_id == incident_id]
        if dataset_id is not None:
            results = [r for r in results if r.dataset_id == dataset_id]
        if dataset_version_id is not None:
            results = [r for r in results if r.dataset_version_id == dataset_version_id]
        return results


def _persisted_incident(incident_id, severity=AnomalySeverity.CRITICAL, anomalies=()):
    return PersistedIncident(id=incident_id, severity=severity, anomalies=anomalies)


def _persisted_root_cause(incident_id, cause=RootCause.SERVICE_OUTAGE, confidence_score=85, confidence_level="High"):
    return PersistedRootCause(
        id=uuid.uuid4(), incident_id=incident_id, cause=cause, confidence_score=confidence_score,
        confidence_level=confidence_level,
    )


def _engine():
    return BusinessImpactEngine(rules=default_rules())


@pytest.mark.anyio
async def test_create_assessment_runs_engine_and_persists_result():
    incident_id = uuid.uuid4()
    anomalies = (
        PersistedActiveAnomaly(
            id=uuid.uuid4(), type=AnomalyType.COMPLAINT_SPIKE, entity_type="global", entity_value=None,
            baseline_value=100.0, current_value=200.0, percentage_change=100.0,
        ),
    )
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id, anomalies=anomalies)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    assessment = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    assert assessment.incident_id == incident_id
    assert assessment.assessment_id is not None
    assert business_impact_repo.by_id[assessment.assessment_id] is assessment
    # Critical severity + 100% volume increase -> FinancialRule fires CRITICAL.
    assert assessment.financial == ImpactLevel.CRITICAL


@pytest.mark.anyio
async def test_create_assessment_raises_not_found_for_missing_incident():
    incident_repo = FakeIncidentReadRepository({})
    root_cause_repo = FakeRootCauseReadRepository({})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    with pytest.raises(IncidentNotFoundError):
        await service.create_assessment(uuid.uuid4(), DATASET_ID, DATASET_VERSION_ID)


@pytest.mark.anyio
async def test_create_assessment_raises_not_found_when_root_cause_missing():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    with pytest.raises(RootCauseNotFoundError):
        await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)


@pytest.mark.anyio
async def test_create_assessment_allows_multiple_assessments_per_incident():
    # Assessments are immutable snapshots -- no one-per-incident constraint,
    # unlike RootCause. Re-running analysis creates a new assessment.
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    first = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)
    second = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    assert first.assessment_id != second.assessment_id
    assert len(business_impact_repo.by_id) == 2


@pytest.mark.anyio
async def test_get_assessment_returns_none_when_missing():
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(
        FakeIncidentReadRepository({}), FakeRootCauseReadRepository({}), business_impact_repo, _engine()
    )

    assert await service.get_assessment(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_get_assessment_returns_the_persisted_record():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    created = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)
    fetched = await service.get_assessment(created.assessment_id)

    assert fetched is created


@pytest.mark.anyio
async def test_list_assessments_filters_by_incident_id():
    incident_id_1, incident_id_2 = uuid.uuid4(), uuid.uuid4()
    incident_repo = FakeIncidentReadRepository(
        {incident_id_1: _persisted_incident(incident_id_1), incident_id_2: _persisted_incident(incident_id_2)}
    )
    root_cause_repo = FakeRootCauseReadRepository(
        {incident_id_1: _persisted_root_cause(incident_id_1), incident_id_2: _persisted_root_cause(incident_id_2)}
    )
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    await service.create_assessment(incident_id_1, DATASET_ID, DATASET_VERSION_ID)
    await service.create_assessment(incident_id_2, DATASET_ID, DATASET_VERSION_ID)

    results = await service.list_assessments(incident_id=incident_id_1)

    assert len(results) == 1
    assert results[0].incident_id == incident_id_1


@pytest.mark.anyio
async def test_list_assessments_filters_by_severity_and_priority():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id, severity=AnomalySeverity.LOW)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id, cause=RootCause.UNKNOWN)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    created = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    matching = await service.list_assessments(severity=created.overall_severity, priority=created.business_priority)
    non_matching = await service.list_assessments(severity=ImpactLevel.CRITICAL)

    assert len(matching) == 1
    assert non_matching == []


@pytest.mark.anyio
async def test_list_assessments_returns_all_when_no_filters_given():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    assert len(await service.list_assessments()) == 1


class _RecordingPublisher:
    def __init__(self) -> None:
        self.published = []

    async def publish(self, event) -> list:
        self.published.append(event)
        return []


class _FailingPublisher:
    async def publish(self, event) -> list:
        raise RuntimeError("simulated publisher failure")


@pytest.mark.anyio
async def test_create_assessment_publishes_a_completed_event_when_a_publisher_is_configured():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    publisher = _RecordingPublisher()
    service = BusinessImpactApplicationService(
        incident_repo, root_cause_repo, business_impact_repo, _engine(), event_publisher=publisher
    )

    assessment = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    assert len(publisher.published) == 1
    event = publisher.published[0]
    assert event.incident_id == incident_id
    assert event.assessment is assessment
    # event_id and incident_id are kept semantically distinct -- never the same value.
    assert event.event_id != incident_id


@pytest.mark.anyio
async def test_create_assessment_mints_a_fresh_event_id_for_every_assessment():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    publisher = _RecordingPublisher()
    service = BusinessImpactApplicationService(
        incident_repo, root_cause_repo, business_impact_repo, _engine(), event_publisher=publisher
    )

    await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)
    await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    assert len(publisher.published) == 2
    assert publisher.published[0].event_id != publisher.published[1].event_id


@pytest.mark.anyio
async def test_no_event_is_published_when_no_publisher_is_configured():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    # Must not raise merely because no publisher was configured.
    assessment = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)
    assert assessment is not None


@pytest.mark.anyio
async def test_a_publisher_failure_never_fails_or_rolls_back_the_already_persisted_assessment():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(
        incident_repo, root_cause_repo, business_impact_repo, _engine(), event_publisher=_FailingPublisher()
    )

    assessment = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    assert assessment is not None
    assert business_impact_repo.by_id[assessment.assessment_id] is assessment


@pytest.fixture
def anyio_backend():
    return "asyncio"
