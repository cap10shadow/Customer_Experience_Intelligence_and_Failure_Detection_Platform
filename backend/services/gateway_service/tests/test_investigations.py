import uuid

import httpx
import pytest

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

INCIDENT_ID = str(uuid.uuid4())
ANOMALY_ID_1 = str(uuid.uuid4())
ANOMALY_ID_2 = str(uuid.uuid4())
RECOMMENDATION_ID = str(uuid.uuid4())


def _incident():
    return {
        "id": INCIDENT_ID,
        "incident_key": "checkout-failures",
        "title": "Checkout failures rising",
        "severity": "high",
        "status": "open",
        "confidence_score": 82,
        "summary": "Payment failures are trending above baseline.",
        "started_at": "2026-08-08T00:00:00Z",
        "last_updated_at": "2026-08-08T01:00:00Z",
        "resolved_at": None,
    }


def _anomaly(anomaly_id):
    return {
        "id": anomaly_id,
        "fingerprint": "complaint_spike:global:ALL",
        "type": "complaint_spike",
        "severity": "high",
        "entity_type": "global",
        "entity_value": None,
        "baseline_value": 10,
        "current_value": 30,
        "percentage_change": 200.0,
        "triggered_rule": "percentage_change magnitude 200.0% in (100%, 200%] -> HIGH",
        "explanation": "complaint_spike detected for global: baseline=10, current=30, change=+200.0%, severity=high.",
        "first_detected_at": "2026-08-08T00:00:00Z",
        "last_seen_at": "2026-08-08T00:30:00Z",
        "status": "active",
    }


def _root_cause():
    return {
        "id": str(uuid.uuid4()),
        "incident_id": INCIDENT_ID,
        "cause": "payment_gateway_failure",
        "confidence_score": 85,
        "confidence_level": "High",
        "evidence": [],
        "explanation": "The timing aligns with a recent payment gateway change.",
        "rule_version": "1.0",
        "status": "identified",
        "created_at": "2026-08-08T01:00:00Z",
        "updated_at": "2026-08-08T01:00:00Z",
    }


def _business_impact(confidence=100):
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
        "confidence": confidence,
        "estimated_affected_customers": 500,
        "explanation": "explanation",
        "status": "assessed",
        "created_at": "2026-08-08T01:10:00Z",
        "updated_at": "2026-08-08T01:10:00Z",
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


def _json(payload, status_code=200):
    return httpx.Response(status_code, json=payload)


def _make_handler(
    *,
    incident_status=200,
    anomalies=None,
    anomalies_status=200,
    root_cause_status=200,
    business_impact_status=200,
    business_impact_items=None,
    recommendation_status=200,
    recommendation_items=None,
):
    anomalies = anomalies if anomalies is not None else [_anomaly(ANOMALY_ID_1), _anomaly(ANOMALY_ID_2)]
    business_impact_items = business_impact_items if business_impact_items is not None else [_business_impact()]
    recommendation_items = recommendation_items if recommendation_items is not None else [_recommendation()]

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith("/anomalies"):
            if anomalies_status != 200:
                return httpx.Response(anomalies_status)
            return _json(anomalies)

        if path.endswith(f"/incidents/{INCIDENT_ID}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            if incident_status == 404:
                return httpx.Response(404)
            if incident_status != 200:
                return httpx.Response(incident_status)
            return _json(_incident())

        if path.endswith("/root-cause"):
            if root_cause_status == 404:
                return httpx.Response(404)
            if root_cause_status != 200:
                return httpx.Response(root_cause_status)
            return _json(_root_cause())

        if path.endswith("/business-impact"):
            if business_impact_status != 200:
                return httpx.Response(business_impact_status)
            return _json(business_impact_items)

        if path.endswith("/recommendations/latest"):
            if recommendation_status != 200:
                return httpx.Response(recommendation_status)
            return _json(recommendation_items)

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
async def test_investigation_aggregates_real_downstream_data(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()

    assert body["incidentId"] == INCIDENT_ID
    assert body["observation"] == {"headline": "Checkout failures rising", "description": "Payment failures are trending above baseline."}

    assert len(body["evidence"]) == 3  # 2 anomalies + 1 correlation synthesis
    sources = [item["source"] for item in body["evidence"]]
    assert sources.count("Anomaly Detection") == 2
    assert sources.count("Incident Correlation") == 1
    assert "NLP Intelligence" not in sources  # no real capability sources this today

    assert body["rootCause"]["confidenceLevel"] == "high"  # "High" band -> high
    assert "Payment Gateway Failure" in body["rootCause"]["headline"]

    assert len(body["businessImpact"]) == 5
    dimensions = {item["dimension"] for item in body["businessImpact"]}
    assert dimensions == {"financial", "customer", "operational", "sla", "reputation"}
    # ARB-008: business_impact_service has no stage-specific confidence
    # classification of its own -- the Gateway must not invent one, even
    # though the fixture's raw confidence=100 exists (see the dedicated
    # ARB-008 regression tests below for the full rationale).
    assert body["businessImpactConfidenceLevel"] is None

    assert body["recommendedNextStep"]["recommendationId"] == RECOMMENDATION_ID
    assert body["recommendedNextStep"]["headline"] == "Escalate to payments team"

    assert body["warnings"] == []


@pytest.mark.anyio
async def test_incident_not_found_returns_a_real_404_not_a_generic_failure(override_http_client):
    client = _client_for(_make_handler(incident_status=404))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert body["error"]["details"]["incidentId"] == INCIDENT_ID


@pytest.mark.anyio
async def test_incident_service_failure_fails_the_whole_request(override_http_client):
    client = _client_for(_make_handler(incident_status=500))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"


@pytest.mark.anyio
async def test_root_cause_not_yet_identified_is_a_legitimate_null_not_a_warning(override_http_client):
    client = _client_for(_make_handler(root_cause_status=404))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["rootCause"] is None
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_root_cause_service_failure_fails_the_whole_request_as_essential(override_http_client):
    """Batch 1 SS14's own example groups root cause with 'core incident, findings' as required."""
    client = _client_for(_make_handler(root_cause_status=503))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    # A non-2xx HTTP response (as opposed to a connection failure/timeout)
    # maps to 502 DOWNSTREAM_SERVICE_FAILURE, consistent with Dashboard's
    # essential-failure convention (Part 2).
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"


@pytest.mark.anyio
async def test_business_impact_not_yet_assessed_is_a_legitimate_empty_not_a_warning(override_http_client):
    client = _client_for(_make_handler(business_impact_items=[]))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["businessImpact"] == []
    assert body["businessImpactConfidenceLevel"] is None
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_business_impact_service_failure_degrades_as_non_essential(override_http_client):
    """Batch 1 SS14's own example explicitly names business impact as the one allowed to be 'unavailable' in a degraded response."""
    client = _client_for(_make_handler(business_impact_status=503))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["businessImpact"] == []
    assert any("Business impact" in warning for warning in body["warnings"])
    # The rest of the Investigation still renders.
    assert body["rootCause"] is not None


@pytest.mark.anyio
async def test_no_recommendation_yet_is_a_legitimate_null_not_a_warning(override_http_client):
    client = _client_for(_make_handler(recommendation_items=[]))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["recommendedNextStep"] is None
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_recommendation_service_failure_degrades_as_non_essential(override_http_client):
    client = _client_for(_make_handler(recommendation_status=503))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["recommendedNextStep"] is None
    assert any("Recommendation data" in warning for warning in body["warnings"])


@pytest.mark.anyio
async def test_anomaly_evidence_failure_degrades_as_non_essential(override_http_client):
    client = _client_for(_make_handler(anomalies_status=503))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence"] == []
    assert any("Anomaly evidence" in warning for warning in body["warnings"])
    # incident/observation still present -- Evidence failing doesn't fail the whole Investigation.
    assert body["observation"]["headline"] == "Checkout failures rising"


@pytest.mark.anyio
async def test_single_anomaly_produces_no_correlation_synthesis_item(override_http_client):
    client = _client_for(_make_handler(anomalies=[_anomaly(ANOMALY_ID_1)]))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    body = response.json()
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["source"] == "Anomaly Detection"


@pytest.mark.anyio
async def test_incident_id_is_preserved_through_the_full_aggregate(override_http_client):
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.json()["incidentId"] == INCIDENT_ID


# ---------------------------------------------------------------------------
# ARB-008 (Confidence Remains Stage-Specific) regression tests.
#
# business_impact_service exposes only a raw `confidence: int` with no
# stage-specific band classification of its own. The Gateway must never
# convert that raw number into a ConfidenceLevel -- in particular, must
# never reuse root_cause_service's confidence bands to do it, since those
# bands are Root-Cause-domain semantics (see
# backend/services/gateway_service/app/core/confidence.py's docstring).
# These tests would fail if that conversion were ever reintroduced.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "raw_confidence",
    [
        0,  # would be "Weak" -> "low" under Root Cause bands
        20,  # would be "Weak" -> "low"
        45,  # would be "Low" -> "low"
        65,  # would be "Medium" -> "moderate"
        85,  # would be "High" -> "high"
        95,  # would be "Very High" -> "high"
        100,  # would be "Very High" -> "high"
    ],
)
async def test_business_impact_raw_confidence_never_becomes_a_confidence_level(override_http_client, raw_confidence):
    """No raw confidence value -- including ones that would map to every distinct Root Cause band -- may produce a non-null businessImpactConfidenceLevel."""
    client = _client_for(_make_handler(business_impact_items=[_business_impact(confidence=raw_confidence)]))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    assert response.json()["businessImpactConfidenceLevel"] is None


@pytest.mark.anyio
async def test_business_impact_dimension_summaries_are_unaffected_by_the_confidence_correction(override_http_client):
    """The ARB-008 correction touches only businessImpactConfidenceLevel -- the five dimension summaries themselves must remain exactly as before."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    body = response.json()
    assert len(body["businessImpact"]) == 5
    dimensions = {item["dimension"] for item in body["businessImpact"]}
    assert dimensions == {"financial", "customer", "operational", "sla", "reputation"}


@pytest.mark.anyio
async def test_root_cause_confidence_classification_is_unchanged_by_the_arb008_correction(override_http_client):
    """Root Cause's own confidence mapping (band_to_confidence_level) is untouched -- only the Business Impact reuse of it was removed."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    body = response.json()
    assert body["rootCause"]["confidenceLevel"] == "high"  # fixture's "High" band -> "high", same as before
