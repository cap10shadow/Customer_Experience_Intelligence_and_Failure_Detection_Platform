import asyncio
import time
import uuid

import httpx
import pytest

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

INCIDENT_ID = str(uuid.uuid4())
RESOLVED_INCIDENT_ID = str(uuid.uuid4())
RECOMMENDATION_ID = str(uuid.uuid4())


def _incident(incident_id=INCIDENT_ID, *, status="open", severity="high"):
    return {
        "id": incident_id,
        "incident_key": "checkout-failures",
        "title": "Checkout failures rising",
        "severity": severity,
        "status": status,
        "confidence_score": 82,
        "summary": "Payment failures are trending above baseline.",
        "started_at": "2026-08-08T00:00:00Z",
        "last_updated_at": "2026-08-08T01:00:00Z",
        "resolved_at": None,
    }


def _volume_trend():
    return {
        "period": "Last 1 Days",
        "complaint_volume": [
            {"date": "2026-08-07", "count": 30},
            {"date": "2026-08-08", "count": 42},
        ],
    }


def _recommendation():
    return {
        "recommendation_id": RECOMMENDATION_ID,
        "incident_id": INCIDENT_ID,
        "generation_id": str(uuid.uuid4()),
        "category": "escalate",
        "priority": "high",
        "score": 88,
        "action": "Escalate to payments team",
        "created_at": "2026-08-08T01:05:00Z",
    }


def _root_cause():
    return {
        "id": str(uuid.uuid4()),
        "incident_id": INCIDENT_ID,
        "cause": "payment_provider_outage",
        "confidence_score": 80,
        "confidence_level": "high",
        "evidence": [],
        "explanation": "explanation",
        "rule_version": "v1",
        "status": "identified",
        "created_at": "2026-08-08T01:00:00Z",
        "updated_at": "2026-08-08T01:00:00Z",
    }


def _business_impact():
    return {
        "assessment_id": str(uuid.uuid4()),
        "incident_id": INCIDENT_ID,
        "root_cause_id": str(uuid.uuid4()),
        "financial": "high",
        "customer": "high",
        "operational": "medium",
        "sla": "medium",
        "reputation": "low",
        "overall_score": 70,
        "overall_severity": "high",
        "business_priority": "high",
        "confidence": 75,
        "estimated_affected_customers": 500,
        "explanation": "explanation",
        "status": "assessed",
        "created_at": "2026-08-08T01:10:00Z",
        "updated_at": "2026-08-08T01:10:00Z",
    }


def _json(payload, status_code=200):
    return httpx.Response(status_code, json=payload)


def _make_handler(*, incidents=None, trend_status=200, recommendations_status=200, root_cause_status=200, business_impact_status=200, delays=None):
    """
    Builds an async httpx.MockTransport handler that routes by URL, so one
    fake "downstream cluster" can stand in for all four real services in a
    single test. `delays` optionally injects an artificial async sleep per
    path segment, used only by the concurrency test.
    """
    incidents = incidents if incidents is not None else [_incident()]
    delays = delays or {}

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith("/incidents") and settings.ANOMALY_SERVICE_URL in str(request.url):
            if "incidents" in delays:
                await asyncio.sleep(delays["incidents"])
            return _json(incidents)

        if path.endswith("/trends/daily"):
            if "trends" in delays:
                await asyncio.sleep(delays["trends"])
            if trend_status != 200:
                return httpx.Response(trend_status)
            return _json(_volume_trend())

        if path.endswith("/recommendations"):
            if "recommendations" in delays:
                await asyncio.sleep(delays["recommendations"])
            if recommendations_status != 200:
                return httpx.Response(recommendations_status)
            return _json([_recommendation()])

        if path.endswith("/root-cause"):
            if root_cause_status == 404:
                return httpx.Response(404)
            if root_cause_status != 200:
                return httpx.Response(root_cause_status)
            return _json(_root_cause())

        if path.endswith("/business-impact"):
            if business_impact_status != 200:
                return httpx.Response(business_impact_status)
            return _json([_business_impact()])

        raise AssertionError(f"Unexpected downstream call: {request.url}")

    return handler


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def override_http_client():
    def _apply(client: httpx.AsyncClient):
        app.dependency_overrides[get_http_client] = lambda: client

    yield _apply
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_dashboard_aggregates_real_downstream_data(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    assert response.status_code == 200
    body = response.json()

    assert body["operationalBrief"]["level"] == "critical"  # severity=high -> critical
    assert "1 active incident(s)" in body["operationalBrief"]["summary"]
    assert body["operationalBrief"]["healthIndicators"][0]["trend"] == "up"
    assert body["operationalBrief"]["criticalSituations"][0]["headline"] == "Checkout failures rising"

    assert body["decisionSummary"][0]["id"] == RECOMMENDATION_ID
    assert body["decisionSummary"][0]["headline"] == "Escalate to payments team"
    assert body["decisionSummary"][0]["importance"] == "high"

    story = body["investigationEntryPoints"][0]
    assert story["id"] == INCIDENT_ID
    assert "Payment Provider Outage" in story["direction"]
    assert "high severity" in story["context"]

    assert body["appliedFilters"]["timeRange"] == "current"
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_decision_summary_never_claims_a_lifecycle_or_approval_state(override_http_client):
    """P1-1: Decision Summary is descriptive only -- no fabricated decision/lifecycle state."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    opportunity = response.json()["decisionSummary"][0]
    combined_text = " ".join([opportunity["headline"], opportunity["reason"], opportunity["nextDecision"]]).lower()

    for forbidden in ("awaiting approval", "pending decision", "approved", "rejected", "deferred", "decision owner"):
        assert forbidden not in combined_text


@pytest.mark.anyio
async def test_resolved_incidents_are_excluded_from_active_sections(override_http_client):
    incidents = [_incident(), _incident(RESOLVED_INCIDENT_ID, status="resolved", severity="critical")]
    client = _client_for(_make_handler(incidents=incidents))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    body = response.json()
    situation_ids = [situation["id"] for situation in body["operationalBrief"]["criticalSituations"]]
    assert RESOLVED_INCIDENT_ID not in situation_ids
    # The resolved incident is CRITICAL severity but excluded, so the open HIGH incident should still drive the level.
    assert body["operationalBrief"]["level"] == "critical"


@pytest.mark.anyio
async def test_root_cause_not_yet_identified_degrades_gracefully_not_as_a_failure(override_http_client):
    client = _client_for(_make_handler(root_cause_status=404))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    assert response.status_code == 200
    story = response.json()["investigationEntryPoints"][0]
    assert "has not yet been completed" in story["direction"]
    assert response.json()["warnings"] == []  # 404 is a legitimate "not found", not a failure/warning


@pytest.mark.anyio
async def test_essential_incidents_failure_fails_the_whole_request(override_http_client):
    async def failing_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/incidents"):
            return httpx.Response(500)
        raise AssertionError("Should not reach other downstream calls' assertions in this test")

    client = _client_for(failing_handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"
    assert body["error"]["requestId"]


@pytest.mark.anyio
async def test_non_essential_trend_failure_degrades_with_a_warning_not_a_total_failure(override_http_client):
    client = _client_for(_make_handler(trend_status=503))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["operationalBrief"]["healthIndicators"] == []
    assert body["operationalBrief"]["keyChanges"] == []
    assert any("Complaint volume trend" in warning for warning in body["warnings"])


@pytest.mark.anyio
async def test_non_essential_recommendation_failure_degrades_with_a_warning(override_http_client):
    client = _client_for(_make_handler(recommendations_status=503))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["decisionSummary"] == []
    assert any("Recommendation data" in warning for warning in body["warnings"])


@pytest.mark.anyio
async def test_invalid_time_range_returns_400(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard", params={"timeRange": "last-quarter"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
@pytest.mark.parametrize("field,value", [("region", "EMEA"), ("businessUnit", "payments"), ("productScope", "checkout"), ("userScope", "self")])
async def test_no_fake_filter_rule_rejects_unsupported_filters(override_http_client, field, value):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard", params={field: value})

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert field in body["error"]["details"]["unsupportedFilters"]


@pytest.mark.anyio
async def test_no_fake_filter_rule_allows_a_blank_or_absent_filter(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard", params={"region": ""})

    assert response.status_code == 200


@pytest.mark.anyio
async def test_time_range_maps_to_the_real_days_window(override_http_client):
    seen_days = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/incidents"):
            return _json([_incident()])
        if request.url.path.endswith("/trends/daily"):
            seen_days["days"] = request.url.params.get("days")
            return _json(_volume_trend())
        if request.url.path.endswith("/recommendations"):
            return _json([])
        if request.url.path.endswith("/root-cause"):
            return httpx.Response(404)
        if request.url.path.endswith("/business-impact"):
            return _json([])
        raise AssertionError(f"unexpected {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard", params={"timeRange": "30d"})

    assert response.status_code == 200
    assert seen_days["days"] == "30"


@pytest.mark.anyio
async def test_incidents_trends_and_recommendations_are_fetched_concurrently(override_http_client):
    delay_seconds = 0.05
    client = _client_for(
        _make_handler(delays={"incidents": delay_seconds, "trends": delay_seconds, "recommendations": delay_seconds})
    )
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        start = time.perf_counter()
        response = await test_client.get("/api/v1/dashboard")
        elapsed = time.perf_counter() - start

    assert response.status_code == 200
    # Sequential would take >= 3 * delay_seconds; concurrent stays well under that.
    assert elapsed < delay_seconds * 3


@pytest.mark.anyio
async def test_no_more_than_two_incidents_are_enriched_with_root_cause_and_business_impact(override_http_client):
    incidents = [_incident(str(uuid.uuid4()), severity="critical") for _ in range(5)]
    root_cause_calls = []
    business_impact_calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/incidents"):
            return _json(incidents)
        if request.url.path.endswith("/trends/daily"):
            return _json(_volume_trend())
        if request.url.path.endswith("/recommendations"):
            return _json([])
        if request.url.path.endswith("/root-cause"):
            root_cause_calls.append(request.url.path)
            return httpx.Response(404)
        if request.url.path.endswith("/business-impact"):
            business_impact_calls.append(request.url.path)
            return _json([])
        raise AssertionError(f"unexpected {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert len(response.json()["investigationEntryPoints"]) == 2
    assert len(root_cause_calls) == 2
    assert len(business_impact_calls) == 2
