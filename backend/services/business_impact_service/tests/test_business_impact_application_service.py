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

    async def list(self, *, severity=None, priority=None, incident_id=None):
        results = list(self.by_id.values())
        if severity is not None:
            results = [r for r in results if r.overall_severity == severity]
        if priority is not None:
            results = [r for r in results if r.business_priority == priority]
        if incident_id is not None:
            results = [r for r in results if r.incident_id == incident_id]
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

    assessment = await service.create_assessment(incident_id)

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
        await service.create_assessment(uuid.uuid4())


@pytest.mark.anyio
async def test_create_assessment_raises_not_found_when_root_cause_missing():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    with pytest.raises(RootCauseNotFoundError):
        await service.create_assessment(incident_id)


@pytest.mark.anyio
async def test_create_assessment_allows_multiple_assessments_per_incident():
    # Assessments are immutable snapshots -- no one-per-incident constraint,
    # unlike RootCause. Re-running analysis creates a new assessment.
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseReadRepository({incident_id: _persisted_root_cause(incident_id)})
    business_impact_repo = FakeBusinessImpactRepository()
    service = BusinessImpactApplicationService(incident_repo, root_cause_repo, business_impact_repo, _engine())

    first = await service.create_assessment(incident_id)
    second = await service.create_assessment(incident_id)

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

    created = await service.create_assessment(incident_id)
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

    await service.create_assessment(incident_id_1)
    await service.create_assessment(incident_id_2)

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

    created = await service.create_assessment(incident_id)

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

    await service.create_assessment(incident_id)

    assert len(await service.list_assessments()) == 1


@pytest.fixture
def anyio_backend():
    return "asyncio"
