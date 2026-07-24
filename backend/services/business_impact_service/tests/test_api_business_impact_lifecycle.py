"""
Phase 7 Step 3 -- API Integration Tests.

Unlike `test_api_business_impact.py` (Phase 7 Step 2), which validates the
REST contract in isolation against a mocked Application Service, these tests
override only the repository-level dependencies with Fakes and let the real
`BusinessImpactApplicationService`, real `BusinessImpactEngine`, real
mappers, and real DTOs run for every request. This validates that the REST
layer is correctly wired to the real orchestration, not just that the route
shapes match a contract.

No new endpoints, no new DTO fields, and no API contract changes are
introduced -- these tests exercise the existing, frozen contract only.
"""

import uuid
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from backend.services.business_impact_service.app.dependencies.services import (
    get_business_impact_repository,
    get_incident_read_repository,
    get_root_cause_read_repository,
)
from backend.services.business_impact_service.app.main import app
from backend.services.business_impact_service.tests.fakes import (
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


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def wired_scenario():
    """
    Overrides only the repository dependencies with Fakes pre-loaded with one
    realistic scenario, leaving the real Application Service, real Engine,
    and real mappers to run for every request made against `app` during the
    test. Yields (incident_id, persisted_root_cause) for assertions.
    """
    incident_id, persisted_incident, persisted_root_cause = build_realistic_incident_scenario()
    # A single shared instance: the (Fake) write repository must retain its
    # in-memory state across the multiple requests one test may issue,
    # exactly as a real repository's backing database would.
    business_impact_repo = FakeBusinessImpactRepository()

    app.dependency_overrides[get_incident_read_repository] = lambda: FakeIncidentReadRepository(
        {incident_id: persisted_incident}
    )
    app.dependency_overrides[get_root_cause_read_repository] = lambda: FakeRootCauseReadRepository(
        {incident_id: persisted_root_cause}
    )
    app.dependency_overrides[get_business_impact_repository] = lambda: business_impact_repo

    yield incident_id, persisted_root_cause

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_post_business_impact_returns_a_fully_computed_assessment(wired_scenario):
    incident_id, persisted_root_cause = wired_scenario

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/business-impact", json={"incident_id": str(incident_id)})

    assert response.status_code == 201
    body = response.json()
    assert body["incident_id"] == str(incident_id)
    assert body["root_cause_id"] == str(persisted_root_cause.id)
    assert body["financial"] == EXPECTED_FINANCIAL.value
    assert body["customer"] == EXPECTED_CUSTOMER.value
    assert body["operational"] == EXPECTED_OPERATIONAL.value
    assert body["sla"] == EXPECTED_SLA.value
    assert body["reputation"] == EXPECTED_REPUTATION.value
    assert body["overall_score"] == EXPECTED_OVERALL_SCORE
    assert body["overall_severity"] == EXPECTED_OVERALL_SEVERITY.value
    assert body["business_priority"] == EXPECTED_BUSINESS_PRIORITY.value
    assert body["confidence"] == EXPECTED_CONFIDENCE
    assert body["estimated_affected_customers"] == EXPECTED_AFFECTED_CUSTOMERS
    assert body["explanation"] == EXPECTED_EXPLANATION
    assert body["status"] == "active"
    # Timestamp serialization: parseable ISO-8601.
    datetime.fromisoformat(body["created_at"])
    datetime.fromisoformat(body["updated_at"])


@pytest.mark.anyio
async def test_get_business_impact_by_assessment_id_round_trips(wired_scenario):
    incident_id, _persisted_root_cause = wired_scenario

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post("/api/v1/business-impact", json={"incident_id": str(incident_id)})
        assessment_id = created.json()["assessment_id"]

        fetched = await client.get(f"/api/v1/business-impact/{assessment_id}")

    assert fetched.status_code == 200
    assert fetched.json() == created.json()


@pytest.mark.anyio
async def test_get_business_impact_by_assessment_id_404_when_missing(wired_scenario):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/api/v1/business-impact/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_business_impact_by_assessment_id_422_for_malformed_uuid(wired_scenario):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/business-impact/not-a-valid-uuid")

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_business_impact_404_for_unknown_incident_id(wired_scenario):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/business-impact", json={"incident_id": str(uuid.uuid4())})

    assert response.status_code == 404


@pytest.mark.anyio
async def test_post_business_impact_422_for_malformed_incident_id(wired_scenario):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/business-impact", json={"incident_id": "not-a-valid-uuid"})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_business_impact_404_when_incident_has_no_root_cause_yet():
    incident_id, persisted_incident, _persisted_root_cause = build_realistic_incident_scenario()

    app.dependency_overrides[get_incident_read_repository] = lambda: FakeIncidentReadRepository(
        {incident_id: persisted_incident}
    )
    app.dependency_overrides[get_root_cause_read_repository] = lambda: FakeRootCauseReadRepository({})
    app.dependency_overrides[get_business_impact_repository] = lambda: FakeBusinessImpactRepository()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/v1/business-impact", json={"incident_id": str(incident_id)})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_list_business_impact_retrieves_by_incident_id(wired_scenario):
    """
    "Retrieval by incident id" is served by the existing list endpoint's
    incident_id filter -- there is no dedicated per-incident endpoint (by
    design: unlike RootCause, multiple assessments may exist per incident).
    """
    incident_id, _persisted_root_cause = wired_scenario

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/api/v1/business-impact", json={"incident_id": str(incident_id)})

        response = await client.get("/api/v1/business-impact", params={"incident_id": str(incident_id)})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["incident_id"] == str(incident_id)


@pytest.mark.anyio
async def test_list_business_impact_filters_by_severity_and_priority(wired_scenario):
    incident_id, _persisted_root_cause = wired_scenario

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/api/v1/business-impact", json={"incident_id": str(incident_id)})

        matching = await client.get(
            "/api/v1/business-impact",
            params={"severity": EXPECTED_OVERALL_SEVERITY.value, "priority": EXPECTED_BUSINESS_PRIORITY.value},
        )
        non_matching = await client.get("/api/v1/business-impact", params={"severity": "critical"})

    assert len(matching.json()) == 1
    assert non_matching.json() == []


@pytest.mark.anyio
async def test_list_business_impact_422_for_invalid_severity_filter(wired_scenario):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/business-impact", params={"severity": "not-a-real-level"})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_no_update_endpoint_exists_for_assessments(wired_scenario):
    """Assessments are immutable -- there is no PUT/PATCH route (unchanged since Phase 7 Step 2)."""
    incident_id, _persisted_root_cause = wired_scenario

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post("/api/v1/business-impact", json={"incident_id": str(incident_id)})
        assessment_id = created.json()["assessment_id"]

        response = await client.patch(f"/api/v1/business-impact/{assessment_id}")

    assert response.status_code == 405
