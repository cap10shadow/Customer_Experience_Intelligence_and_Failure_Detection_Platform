"""
Phase 7 Step 3 -- Lifecycle & Validation.

Validates the complete Business Impact lifecycle end-to-end:

    Incident -> Root Cause Summary -> Business Impact Engine
        -> BusinessImpactAssessment -> Persistence -> Repository
        -> REST response DTO

using one realistic, hand-computable synthetic scenario. Every field is
checked at every boundary -- this is deliberately not a smoke test.

No production code is exercised differently than the real deployment: the
real `BusinessImpactInputMapper`, the real `BusinessImpactEngine` (with the
real `default_rules()`), the real `BusinessImpactOutputMapper`, the real
`BusinessImpactApplicationService`, and the real `BusinessImpactAssessmentResponse`
DTO are all used unmodified. Only the repository layer's database access is
replaced with in-memory Fakes (see `fakes.py`), consistent with this
repository's existing testing convention (no real-database test
infrastructure exists anywhere in this codebase).
"""

import uuid
from datetime import datetime

import pytest

from backend.services.business_impact_service.app.repositories.incident_read_repository import PersistedIncident
from backend.services.business_impact_service.app.schemas.business_impact import BusinessImpactAssessmentResponse
from backend.services.business_impact_service.app.services.business_impact_application_service import (
    BusinessImpactApplicationService,
)
from backend.services.business_impact_service.app.services.exceptions import (
    IncidentNotFoundError,
    RootCauseNotFoundError,
)
from backend.services.business_impact_service.app.services.impact_engine import BusinessImpactEngine, default_rules
from backend.services.business_impact_service.tests.fakes import (
    DATASET_ID,
    DATASET_VERSION_ID,
    EXPECTED_AFFECTED_CUSTOMERS,
    EXPECTED_BUSINESS_PRIORITY,
    EXPECTED_CONFIDENCE,
    EXPECTED_CUSTOMER,
    EXPECTED_EXPLANATION,
    EXPECTED_FINANCIAL,
    EXPECTED_OPERATIONAL,
    EXPECTED_OVERALL_SCORE,
    EXPECTED_OVERALL_SEVERITY,
    EXPECTED_REPUTATION,
    EXPECTED_SLA,
    FakeBusinessImpactRepository,
    FakeIncidentReadRepository,
    FakeRootCauseReadRepository,
    build_realistic_incident_scenario,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _service_with_scenario():
    """Builds the real Application Service (real engine, real mappers), pre-loaded with one realistic scenario."""
    incident_id, persisted_incident, persisted_root_cause = build_realistic_incident_scenario()
    service = BusinessImpactApplicationService(
        incident_read_repository=FakeIncidentReadRepository({incident_id: persisted_incident}),
        root_cause_read_repository=FakeRootCauseReadRepository({incident_id: persisted_root_cause}),
        business_impact_repository=FakeBusinessImpactRepository(),
        engine=BusinessImpactEngine(rules=default_rules()),
    )
    return service, incident_id, persisted_incident, persisted_root_cause


@pytest.mark.anyio
async def test_lifecycle_produces_a_complete_assessment_from_a_synthetic_incident():
    """Incident -> Root Cause Summary -> Engine -> BusinessImpactAssessment -> Persistence -> Repository."""
    service, incident_id, _persisted_incident, persisted_root_cause = _service_with_scenario()

    entity = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    # Persistence / Repository boundary: the entity round-trips through the
    # (Fake) repository's own get(), exactly as the real API layer would use it.
    fetched = await service.get_assessment(entity.assessment_id)
    assert fetched is entity

    # Identity fields.
    assert entity.incident_id == incident_id
    assert entity.root_cause_id == persisted_root_cause.id
    assert entity.assessment_id is not None

    # Every Business Impact dimension, verified against hand-computed
    # expectations for this exact synthetic scenario (see fakes.py).
    assert entity.financial == EXPECTED_FINANCIAL
    assert entity.customer == EXPECTED_CUSTOMER
    assert entity.operational == EXPECTED_OPERATIONAL
    assert entity.sla == EXPECTED_SLA
    assert entity.reputation == EXPECTED_REPUTATION

    # Overall aggregation.
    assert entity.overall_score == EXPECTED_OVERALL_SCORE
    assert entity.overall_severity == EXPECTED_OVERALL_SEVERITY
    assert entity.business_priority == EXPECTED_BUSINESS_PRIORITY
    assert entity.confidence == EXPECTED_CONFIDENCE
    assert entity.estimated_affected_customers == EXPECTED_AFFECTED_CUSTOMERS

    # Explanation fidelity (see also test_explainability_contract.py for a
    # dedicated, deeper fidelity check across every boundary).
    assert entity.explanation == EXPECTED_EXPLANATION

    # Forward-compatibility fields populated at persistence time (Phase 7
    # Step 2): present, but Step 3 introduces no lifecycle behavior.
    assert entity.status is not None
    assert entity.created_at is not None
    assert entity.updated_at is not None


@pytest.mark.anyio
async def test_lifecycle_dto_serialization_preserves_every_field():
    """BusinessImpactAssessment -> Persistence -> Repository -> REST response DTO."""
    service, incident_id, _persisted_incident, persisted_root_cause = _service_with_scenario()
    entity = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)

    dto = BusinessImpactAssessmentResponse.model_validate(entity, from_attributes=True)

    assert dto.assessment_id == entity.assessment_id
    assert dto.incident_id == incident_id
    assert dto.root_cause_id == persisted_root_cause.id
    assert dto.financial == EXPECTED_FINANCIAL
    assert dto.customer == EXPECTED_CUSTOMER
    assert dto.operational == EXPECTED_OPERATIONAL
    assert dto.sla == EXPECTED_SLA
    assert dto.reputation == EXPECTED_REPUTATION
    assert dto.overall_score == EXPECTED_OVERALL_SCORE
    assert dto.overall_severity == EXPECTED_OVERALL_SEVERITY
    assert dto.business_priority == EXPECTED_BUSINESS_PRIORITY
    assert dto.confidence == EXPECTED_CONFIDENCE
    assert dto.estimated_affected_customers == EXPECTED_AFFECTED_CUSTOMERS
    assert dto.explanation == EXPECTED_EXPLANATION
    assert dto.status == entity.status
    assert dto.created_at == entity.created_at
    assert dto.updated_at == entity.updated_at


@pytest.mark.anyio
async def test_lifecycle_json_serialization_uses_lowercase_enum_values_and_iso_timestamps():
    """DTO -> JSON: enum serialization and timestamp serialization, verified over the wire format."""
    service, incident_id, _persisted_incident, _persisted_root_cause = _service_with_scenario()
    entity = await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)
    dto = BusinessImpactAssessmentResponse.model_validate(entity, from_attributes=True)

    payload = dto.model_dump(mode="json")

    assert payload["financial"] == "critical"
    assert payload["customer"] == "critical"
    assert payload["operational"] == "critical"
    assert payload["sla"] == "none"
    assert payload["reputation"] == "none"
    assert payload["overall_severity"] == "high"
    assert payload["business_priority"] == "high"
    assert payload["status"] == "active"
    # ISO-8601 timestamps: parseable, and round-trip to the same instant.
    assert datetime.fromisoformat(payload["created_at"]) == entity.created_at
    assert datetime.fromisoformat(payload["updated_at"]) == entity.updated_at


@pytest.mark.anyio
async def test_lifecycle_raises_incident_not_found_for_unknown_incident():
    service = BusinessImpactApplicationService(
        incident_read_repository=FakeIncidentReadRepository({}),
        root_cause_read_repository=FakeRootCauseReadRepository({}),
        business_impact_repository=FakeBusinessImpactRepository(),
        engine=BusinessImpactEngine(rules=default_rules()),
    )

    with pytest.raises(IncidentNotFoundError):
        await service.create_assessment(uuid.uuid4(), DATASET_ID, DATASET_VERSION_ID)


@pytest.mark.anyio
async def test_lifecycle_raises_root_cause_not_found_when_incident_has_no_root_cause_yet():
    incident_id = uuid.uuid4()
    service = BusinessImpactApplicationService(
        incident_read_repository=FakeIncidentReadRepository(
            {incident_id: PersistedIncident(id=incident_id, severity=AnomalySeverity.LOW, anomalies=())}
        ),
        root_cause_read_repository=FakeRootCauseReadRepository({}),
        business_impact_repository=FakeBusinessImpactRepository(),
        engine=BusinessImpactEngine(rules=default_rules()),
    )

    with pytest.raises(RootCauseNotFoundError):
        await service.create_assessment(incident_id, DATASET_ID, DATASET_VERSION_ID)
