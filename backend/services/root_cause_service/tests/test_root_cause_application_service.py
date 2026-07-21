import uuid

import pytest

from backend.services.root_cause_service.app.repositories.incident_read_repository import (
    PersistedActiveAnomaly,
    PersistedIncident,
)
from backend.services.root_cause_service.app.services.exceptions import (
    IncidentNotFoundError,
    InvalidLifecycleTransitionError,
    RefreshNotAllowedError,
    RootCauseAlreadyExistsError,
    RootCauseNotFoundError,
)
from backend.services.root_cause_service.app.services.root_cause_application_service import (
    RootCauseApplicationService,
)
from backend.services.root_cause_service.app.services.root_cause_engine import RootCauseEngine
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.incident import IncidentStatus
from backend.shared.constants.enums.root_cause import RootCause as RootCauseEnum
from backend.shared.constants.enums.root_cause import RootCauseStatus


class FakeIncidentReadRepository:
    """In-memory stand-in for IncidentReadRepository."""

    def __init__(self, incidents_by_id):
        self._incidents_by_id = incidents_by_id

    async def get_by_id(self, incident_id):
        return self._incidents_by_id.get(incident_id)


class FakeRootCauseRepository:
    """In-memory stand-in for RootCauseRepository, used to exercise the real
    RootCauseApplicationService orchestration logic without a database."""

    def __init__(self):
        self.by_id = {}
        self.by_incident_id = {}

    async def save(self, root_cause):
        root_cause.id = uuid.uuid4()
        self.by_id[root_cause.id] = root_cause
        self.by_incident_id[root_cause.incident_id] = root_cause
        return root_cause

    async def update(self, root_cause):
        return root_cause

    async def get(self, root_cause_id):
        return self.by_id.get(root_cause_id)

    async def get_by_incident(self, incident_id):
        return self.by_incident_id.get(incident_id)

    async def list(self):
        return list(self.by_id.values())


def _persisted_incident(incident_id, **anomaly_kwargs):
    anomalies = anomaly_kwargs.get("anomalies", ())
    return PersistedIncident(
        id=incident_id,
        incident_key="INC-TEST0001",
        title="Test Incident",
        summary="test summary",
        severity=anomaly_kwargs.get("severity", AnomalySeverity.CRITICAL),
        status=IncidentStatus.OPEN,
        confidence_score=anomaly_kwargs.get("confidence_score", 80),
        anomalies=anomalies,
    )


@pytest.mark.anyio
async def test_create_root_cause_runs_engine_and_persists_result():
    incident_id = uuid.uuid4()
    anomalies = (
        PersistedActiveAnomaly(id=uuid.uuid4(), type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="payment_issue"),
    )
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id, anomalies=anomalies)})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    root_cause = await service.create_root_cause(incident_id)

    assert root_cause.incident_id == incident_id
    assert root_cause.cause == RootCauseEnum.PAYMENT_GATEWAY_FAILURE
    assert root_cause.status == RootCauseStatus.IDENTIFIED
    assert root_cause.id is not None
    assert root_cause_repo.by_incident_id[incident_id] is root_cause


@pytest.mark.anyio
async def test_create_root_cause_raises_not_found_for_missing_incident():
    incident_repo = FakeIncidentReadRepository({})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    with pytest.raises(IncidentNotFoundError):
        await service.create_root_cause(uuid.uuid4())


@pytest.mark.anyio
async def test_create_root_cause_raises_conflict_when_already_exists():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id)})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    await service.create_root_cause(incident_id)

    with pytest.raises(RootCauseAlreadyExistsError):
        await service.create_root_cause(incident_id)


@pytest.mark.anyio
async def test_create_root_cause_returns_unknown_when_no_rule_matches():
    incident_id = uuid.uuid4()
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id, anomalies=())})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    root_cause = await service.create_root_cause(incident_id)

    assert root_cause.cause == RootCauseEnum.UNKNOWN
    assert root_cause.confidence_score == 0


@pytest.mark.anyio
async def test_get_root_cause_by_id_and_by_incident():
    incident_id = uuid.uuid4()
    anomalies = (
        PersistedActiveAnomaly(id=uuid.uuid4(), type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="support_issue"),
    )
    incident_repo = FakeIncidentReadRepository({incident_id: _persisted_incident(incident_id, anomalies=anomalies)})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    created = await service.create_root_cause(incident_id)

    by_id = await service.get_root_cause(created.id)
    by_incident = await service.get_root_cause_by_incident(incident_id)

    assert by_id is created
    assert by_incident is created
    assert await service.get_root_cause(uuid.uuid4()) is None
    assert await service.get_root_cause_by_incident(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_list_root_causes():
    incident_id_1, incident_id_2 = uuid.uuid4(), uuid.uuid4()
    incident_repo = FakeIncidentReadRepository(
        {
            incident_id_1: _persisted_incident(incident_id_1),
            incident_id_2: _persisted_incident(incident_id_2),
        }
    )
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    await service.create_root_cause(incident_id_1)
    await service.create_root_cause(incident_id_2)

    all_root_causes = await service.list_root_causes()
    assert len(all_root_causes) == 2


# ------------------------------------------------------------------
# Phase 6 Step 3: lifecycle management (confirm / reject / refresh)
# ------------------------------------------------------------------

async def _service_with_root_cause(incident_id, anomalies=()):
    incidents_by_id = {incident_id: _persisted_incident(incident_id, anomalies=anomalies)}
    incident_repo = FakeIncidentReadRepository(incidents_by_id)
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())
    root_cause = await service.create_root_cause(incident_id)
    return service, root_cause, incidents_by_id


@pytest.mark.anyio
async def test_confirm_identified_root_cause_succeeds():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)

    confirmed = await service.confirm_root_cause(root_cause.id)

    assert confirmed.status == RootCauseStatus.CONFIRMED


@pytest.mark.anyio
async def test_reject_identified_root_cause_succeeds():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)

    rejected = await service.reject_root_cause(root_cause.id)

    assert rejected.status == RootCauseStatus.REJECTED


@pytest.mark.anyio
async def test_confirm_is_idempotent():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)

    await service.confirm_root_cause(root_cause.id)
    confirmed_again = await service.confirm_root_cause(root_cause.id)

    assert confirmed_again.status == RootCauseStatus.CONFIRMED


@pytest.mark.anyio
async def test_reject_is_idempotent():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)

    await service.reject_root_cause(root_cause.id)
    rejected_again = await service.reject_root_cause(root_cause.id)

    assert rejected_again.status == RootCauseStatus.REJECTED


@pytest.mark.anyio
async def test_confirmed_cannot_be_rejected():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)
    await service.confirm_root_cause(root_cause.id)

    with pytest.raises(InvalidLifecycleTransitionError):
        await service.reject_root_cause(root_cause.id)


@pytest.mark.anyio
async def test_rejected_cannot_be_confirmed():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)
    await service.reject_root_cause(root_cause.id)

    with pytest.raises(InvalidLifecycleTransitionError):
        await service.confirm_root_cause(root_cause.id)


@pytest.mark.anyio
async def test_confirm_raises_not_found_for_missing_root_cause():
    incident_repo = FakeIncidentReadRepository({})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    with pytest.raises(RootCauseNotFoundError):
        await service.confirm_root_cause(uuid.uuid4())


@pytest.mark.anyio
async def test_reject_raises_not_found_for_missing_root_cause():
    incident_repo = FakeIncidentReadRepository({})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    with pytest.raises(RootCauseNotFoundError):
        await service.reject_root_cause(uuid.uuid4())


@pytest.mark.anyio
async def test_refresh_re_runs_engine_and_updates_in_place():
    incident_id = uuid.uuid4()
    anomalies = (
        PersistedActiveAnomaly(id=uuid.uuid4(), type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="payment_issue"),
    )
    service, root_cause, incidents_by_id = await _service_with_root_cause(incident_id, anomalies=anomalies)
    original_id = root_cause.id
    assert root_cause.cause == RootCauseEnum.PAYMENT_GATEWAY_FAILURE

    # The underlying incident now looks like a service outage instead.
    incidents_by_id[incident_id] = _persisted_incident(
        incident_id,
        anomalies=(
            PersistedActiveAnomaly(id=uuid.uuid4(), type=AnomalyType.REGIONAL_SPIKE, entity_type="region", entity_value="South"),
        ),
    )

    refreshed = await service.refresh_root_cause(original_id)

    assert refreshed.id == original_id  # same row, not a new one
    assert refreshed.cause == RootCauseEnum.SERVICE_OUTAGE
    assert refreshed.status == RootCauseStatus.IDENTIFIED  # untouched by refresh


@pytest.mark.anyio
async def test_refresh_persists_unknown_and_keeps_identified_status():
    incident_id = uuid.uuid4()
    anomalies = (
        PersistedActiveAnomaly(id=uuid.uuid4(), type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="payment_issue"),
    )
    service, root_cause, incidents_by_id = await _service_with_root_cause(incident_id, anomalies=anomalies)

    # The underlying incident no longer matches any rule.
    incidents_by_id[incident_id] = _persisted_incident(incident_id, anomalies=())

    refreshed = await service.refresh_root_cause(root_cause.id)

    assert refreshed.cause == RootCauseEnum.UNKNOWN
    assert refreshed.status == RootCauseStatus.IDENTIFIED  # no new lifecycle state introduced


@pytest.mark.anyio
async def test_refresh_forbidden_when_confirmed():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)
    await service.confirm_root_cause(root_cause.id)

    with pytest.raises(RefreshNotAllowedError):
        await service.refresh_root_cause(root_cause.id)


@pytest.mark.anyio
async def test_refresh_forbidden_when_rejected():
    incident_id = uuid.uuid4()
    service, root_cause, _ = await _service_with_root_cause(incident_id)
    await service.reject_root_cause(root_cause.id)

    with pytest.raises(RefreshNotAllowedError):
        await service.refresh_root_cause(root_cause.id)


@pytest.mark.anyio
async def test_refresh_raises_not_found_for_missing_root_cause():
    incident_repo = FakeIncidentReadRepository({})
    root_cause_repo = FakeRootCauseRepository()
    service = RootCauseApplicationService(incident_repo, root_cause_repo, RootCauseEngine())

    with pytest.raises(RootCauseNotFoundError):
        await service.refresh_root_cause(uuid.uuid4())


@pytest.mark.anyio
async def test_end_to_end_lifecycle_flow():
    """Persisted Incident -> Rule Engine -> RootCause -> Confirm -> refresh
    rejected -> reject rejected -> verify final lifecycle state."""
    incident_id = uuid.uuid4()
    anomalies = (
        PersistedActiveAnomaly(id=uuid.uuid4(), type=AnomalyType.CATEGORY_SPIKE, entity_type="category", entity_value="payment_issue"),
    )
    service, root_cause, _ = await _service_with_root_cause(incident_id, anomalies=anomalies)
    assert root_cause.status == RootCauseStatus.IDENTIFIED

    confirmed = await service.confirm_root_cause(root_cause.id)
    assert confirmed.status == RootCauseStatus.CONFIRMED

    with pytest.raises(RefreshNotAllowedError):
        await service.refresh_root_cause(root_cause.id)

    with pytest.raises(InvalidLifecycleTransitionError):
        await service.reject_root_cause(root_cause.id)

    final = await service.get_root_cause(root_cause.id)
    assert final.status == RootCauseStatus.CONFIRMED


@pytest.fixture
def anyio_backend():
    return "asyncio"
