"""
Phase 7 Step 3 -- Determinism Verification.

ADR-003 defines the Business Impact Engine as deterministic. These tests
prove identical inputs always produce an identical BusinessImpactAssessment
-- including scores, priorities, severity, and explanations -- at three
levels: the bare domain engine, the full application-service lifecycle, and
the REST API. No randomness is introduced or tolerated at any layer.

Persisted identity fields (assessment_id, created_at, updated_at) are
expected to differ between separate persisted rows -- that is correct
database behavior, not a determinism violation, and is explicitly excluded
from the equality checks below where the lifecycle runs multiple times.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.business_impact_service.app.dependencies.services import (
    get_business_impact_repository,
    get_incident_read_repository,
    get_root_cause_read_repository,
)
from backend.services.business_impact_service.app.domain.anomaly_metrics import AnomalyMetrics
from backend.services.business_impact_service.app.domain.incident import Incident
from backend.services.business_impact_service.app.domain.root_cause_summary import RootCauseSummary
from backend.services.business_impact_service.app.domain.trend_metrics import TrendMetrics
from backend.services.business_impact_service.app.main import app
from backend.services.business_impact_service.app.services.business_impact_application_service import (
    BusinessImpactApplicationService,
)
from backend.services.business_impact_service.app.services.impact_engine import BusinessImpactEngine, default_rules
from backend.services.business_impact_service.tests.fakes import (
    FakeBusinessImpactRepository,
    FakeIncidentReadRepository,
    FakeRootCauseReadRepository,
    build_realistic_incident_scenario,
)
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import UrgencyLabel
from backend.shared.constants.enums.root_cause import RootCause

REPEAT_COUNT = 10

# Fields that must be byte-for-byte identical across independent lifecycle
# runs over the same business inputs. Deliberately excludes assessment_id,
# created_at, and updated_at, which correctly differ per persisted row.
# ORM entity / API response field names.
_DETERMINISTIC_ENTITY_FIELDS = (
    "financial",
    "customer",
    "operational",
    "sla",
    "reputation",
    "overall_score",
    "overall_severity",
    "business_priority",
    "confidence",
    "estimated_affected_customers",
    "explanation",
)

# Domain BusinessImpactAssessment field names (Phase 7 Step 1) -- these
# differ from the ORM entity's field names (e.g. `financial_impact` vs
# `financial`, `business_score` vs `overall_score`); see BusinessImpactOutputMapper.
_DETERMINISTIC_DOMAIN_FIELDS = (
    "financial_impact",
    "customer_impact",
    "operational_impact",
    "sla_impact",
    "reputation_impact",
    "business_score",
    "overall_severity",
    "business_priority",
    "confidence",
    "estimated_affected_customers",
    "explanation",
)


def _build_identical_inputs():
    """Builds a fresh, independent (not reused/aliased) set of domain inputs with fixed values."""
    incident = Incident(
        incident_id="INC-DETERMINISM-0001",
        severity=AnomalySeverity.CRITICAL,
        regions=("us-east", "us-west"),
        urgency_levels=(UrgencyLabel.CRITICAL,),
    )
    root_cause = RootCauseSummary(cause=RootCause.SERVICE_OUTAGE, confidence_score=90, confidence_level="Very High")
    trend_metrics = TrendMetrics(current_volume=500, baseline_volume=200, percentage_change=150.0)
    anomaly_metrics = AnomalyMetrics(
        anomaly_types=(AnomalyType.COMPLAINT_SPIKE, AnomalyType.REGIONAL_SPIKE, AnomalyType.SENTIMENT_SHIFT),
        severity=AnomalySeverity.CRITICAL,
        affected_customer_count=500,
        sla_breach_count=0,
        negative_sentiment_ratio=0.0,
    )
    return incident, root_cause, trend_metrics, anomaly_metrics


def test_engine_is_deterministic_across_independent_identical_domain_inputs():
    """Bare engine level: two independently-constructed, value-identical input graphs must yield an identical assessment."""
    engine = BusinessImpactEngine(rules=default_rules())

    first_assessment = engine.analyze(*_build_identical_inputs())
    second_assessment = engine.analyze(*_build_identical_inputs())

    assert first_assessment is not second_assessment  # independent objects, not aliased
    assert first_assessment == second_assessment  # frozen dataclass equality: every field, including explanation


@pytest.mark.parametrize("run", range(REPEAT_COUNT))
def test_engine_produces_the_same_assessment_on_every_repeated_call(run):
    """No randomness across many repeated calls -- not just two."""
    engine = BusinessImpactEngine(rules=default_rules())
    assessment = engine.analyze(*_build_identical_inputs())

    baseline_engine = BusinessImpactEngine(rules=default_rules())
    baseline = baseline_engine.analyze(*_build_identical_inputs())

    assert assessment == baseline


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_full_lifecycle_is_deterministic_across_repeated_application_service_calls():
    """
    Application Service level: creating an assessment for the same incident
    repeatedly must always compute the same business fields and the same
    explanation, even though each call persists a new, independent row.
    """
    incident_id, persisted_incident, persisted_root_cause = build_realistic_incident_scenario()
    service = BusinessImpactApplicationService(
        incident_read_repository=FakeIncidentReadRepository({incident_id: persisted_incident}),
        root_cause_read_repository=FakeRootCauseReadRepository({incident_id: persisted_root_cause}),
        business_impact_repository=FakeBusinessImpactRepository(),
        engine=BusinessImpactEngine(rules=default_rules()),
    )

    results = [await service.create_assessment(incident_id) for _ in range(REPEAT_COUNT)]

    assessment_ids = {entity.assessment_id for entity in results}
    assert len(assessment_ids) == REPEAT_COUNT  # every run persisted as its own distinct row

    baseline = results[0]
    for entity in results[1:]:
        for field in _DETERMINISTIC_ENTITY_FIELDS:
            assert getattr(entity, field) == getattr(baseline, field), f"field {field!r} was not deterministic"


@pytest.mark.anyio
async def test_full_lifecycle_is_deterministic_over_http():
    """REST API level: repeated POSTs for the same incident return identical business fields in the JSON response."""
    incident_id, persisted_incident, persisted_root_cause = build_realistic_incident_scenario()
    business_impact_repo = FakeBusinessImpactRepository()

    app.dependency_overrides[get_incident_read_repository] = lambda: FakeIncidentReadRepository(
        {incident_id: persisted_incident}
    )
    app.dependency_overrides[get_root_cause_read_repository] = lambda: FakeRootCauseReadRepository(
        {incident_id: persisted_root_cause}
    )
    app.dependency_overrides[get_business_impact_repository] = lambda: business_impact_repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            responses = [
                await client.post("/api/v1/business-impact", json={"incident_id": str(incident_id)})
                for _ in range(REPEAT_COUNT)
            ]
    finally:
        app.dependency_overrides.clear()

    bodies = [response.json() for response in responses]
    assessment_ids = {body["assessment_id"] for body in bodies}
    assert len(assessment_ids) == REPEAT_COUNT

    baseline = bodies[0]
    for body in bodies[1:]:
        for field in _DETERMINISTIC_ENTITY_FIELDS:
            assert body[field] == baseline[field], f"field {field!r} was not deterministic over HTTP"


def test_deterministic_scenario_builder_produces_the_same_business_result_every_call():
    """`build_realistic_incident_scenario()` varies only identifiers (uuid4) between calls -- the business inputs (severity, volumes, entity values, cause, confidence) are fixed, so the resulting engine computation must always match."""
    engine = BusinessImpactEngine(rules=default_rules())

    from backend.services.business_impact_service.app.mappers.input_mapper import BusinessImpactInputMapper

    _first_incident_id, first_persisted_incident, first_persisted_root_cause = build_realistic_incident_scenario()
    _second_incident_id, second_persisted_incident, second_persisted_root_cause = build_realistic_incident_scenario()

    def _analyze(persisted_incident, persisted_root_cause):
        incident = BusinessImpactInputMapper.to_incident(persisted_incident)
        root_cause_summary = BusinessImpactInputMapper.to_root_cause_summary(persisted_root_cause)
        trend_metrics = BusinessImpactInputMapper.to_trend_metrics(persisted_incident)
        anomaly_metrics = BusinessImpactInputMapper.to_anomaly_metrics(persisted_incident)
        return engine.analyze(incident, root_cause_summary, trend_metrics, anomaly_metrics)

    first_assessment = _analyze(first_persisted_incident, first_persisted_root_cause)
    second_assessment = _analyze(second_persisted_incident, second_persisted_root_cause)

    # incident_id differs (it is the random uuid, correctly reflected in the
    # domain Incident) -- every other field, including the explanation, must match.
    assert first_assessment.incident_id != second_assessment.incident_id
    for field in _DETERMINISTIC_DOMAIN_FIELDS:
        assert getattr(first_assessment, field) == getattr(second_assessment, field), f"field {field!r} differed"
