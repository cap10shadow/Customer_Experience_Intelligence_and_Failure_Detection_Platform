import asyncio
import uuid

import httpx
import pytest

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.main import app

INCIDENT_ID = str(uuid.uuid4())
DATASET_ID = str(uuid.uuid4())
DATASET_VERSION_ID = str(uuid.uuid4())
ANOMALY_ID_1 = str(uuid.uuid4())
ANOMALY_ID_2 = str(uuid.uuid4())
RECOMMENDATION_ID = str(uuid.uuid4())


def _incident():
    return {
        "id": INCIDENT_ID,
        "dataset_id": DATASET_ID,
        "last_analysis_version_id": DATASET_VERSION_ID,
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


def _category_anomaly(anomaly_id, entity_value="payment_issue"):
    return {
        "id": anomaly_id,
        "fingerprint": f"category_spike:category:{entity_value}",
        "type": "category_spike",
        "severity": "high",
        "entity_type": "category",
        "entity_value": entity_value,
        "baseline_value": 5,
        "current_value": 18,
        "percentage_change": 260.0,
        "triggered_rule": "percentage_change magnitude 260.0% in (200%, ...] -> HIGH",
        "explanation": f"category_spike detected for category={entity_value}: baseline=5, current=18.",
        "first_detected_at": "2026-08-08T00:00:00Z",
        "last_seen_at": "2026-08-08T00:30:00Z",
        "status": "active",
    }


def _enrichment_summary(issue_category="payment_issue", total_count=3, sentiment_counts=None):
    return {
        "issue_category": issue_category,
        "total_count": total_count,
        "sentiment_counts": sentiment_counts if sentiment_counts is not None else {"negative": 2, "neutral": 1},
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


def _business_impact_confidence_level(confidence: int) -> str:
    """Mirrors business_impact_service's own domain/confidence.py bands (Step 7.X A-05) -- kept as a separate, independently-defined helper here, never imported from Root Cause's equivalent."""
    if confidence <= 40:
        return "Low"
    if confidence <= 80:
        return "Moderate"
    return "High"


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
        # Real field as of Step 7.X A-05 -- business_impact_service now
        # computes and exposes this itself (BusinessImpactAssessmentResponse.
        # confidence_level, a computed field over `confidence`).
        "confidence_level": _business_impact_confidence_level(confidence),
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
    nlp_summary_status=200,
    nlp_summary=None,
    captured_nlp_params=None,
):
    anomalies = anomalies if anomalies is not None else [_anomaly(ANOMALY_ID_1), _anomaly(ANOMALY_ID_2)]
    business_impact_items = business_impact_items if business_impact_items is not None else [_business_impact()]
    recommendation_items = recommendation_items if recommendation_items is not None else [_recommendation()]
    nlp_summary = nlp_summary if nlp_summary is not None else _enrichment_summary()

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

        if path.endswith("/enrichments/summary"):
            if captured_nlp_params is not None:
                captured_nlp_params.append(dict(request.url.params))
            if nlp_summary_status != 200:
                return httpx.Response(nlp_summary_status)
            return _json(nlp_summary)

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
    # Default fixture anomalies are entity_type="global" (no category
    # dimension), so there is honestly no NLP evidence to source -- see
    # the dedicated Step 7.X A-06 tests below for the category-anomaly case.
    assert "NLP Intelligence" not in sources

    assert body["rootCause"]["confidenceLevel"] == "high"  # "High" band -> high
    assert "Payment Gateway Failure" in body["rootCause"]["headline"]

    assert len(body["businessImpact"]) == 5
    dimensions = {item["dimension"] for item in body["businessImpact"]}
    assert dimensions == {"financial", "customer", "operational", "sla", "reputation"}
    # Step 7.X A-05: business_impact_service now exposes its own
    # classification (fixture's raw confidence=100 -> its own "High" band
    # -> Gateway's business_impact_band_to_confidence_level -> "high").
    assert body["businessImpactConfidenceLevel"] == "high"

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
# Step 7.X A-05: business_impact_service now exposes its own stage-specific
# classification (confidence_level, computed from its own confidence int
# via its own, independently-derived bands -- see business_impact_service/
# app/domain/confidence.py). The Gateway must map ONLY business_impact_
# service's own band string (business_impact_band_to_confidence_level) --
# it must never reuse root_cause_service's bands/thresholds
# (band_to_confidence_level) to do it, since those are Root-Cause-domain
# semantics (see backend/services/gateway_service/app/core/confidence.py's
# docstring). These tests would fail if that reuse were ever introduced.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "raw_confidence,expected_level",
    [
        (0, "low"),  # BI band "Low" -> "low"; RC bands would call this "Weak" -> "low" too, but via a different function
        (40, "low"),  # exact BI boundary: <=40 -> "Low"
        (41, "moderate"),  # exact BI boundary: 41 -> "Moderate" (RC bands would call 41 "Low" -> "low" -- proves independence)
        (65, "moderate"),  # RC bands would call this "Medium" -> "moderate" (same frontend label, different function/thresholds)
        (80, "moderate"),  # exact BI boundary: <=80 -> "Moderate"
        (81, "high"),  # exact BI boundary: 81 -> "High" (RC bands would call 81 "High" -> "high" too, but via a different function)
        (100, "high"),
    ],
)
async def test_business_impact_confidence_uses_its_own_bands_not_root_causes(
    override_http_client, raw_confidence, expected_level
):
    """
    Every raw confidence value maps through business_impact_service's OWN
    bands (fixture's _business_impact_confidence_level, mirroring
    business_impact_service/app/domain/confidence.py exactly) -- never
    through Root Cause's. 41 is the decisive proof: BI's own bands call it
    "Moderate" (-> "moderate") while Root Cause's bands would call the same
    raw number "Low" (-> "low") -- if the Gateway ever accidentally reused
    Root Cause's classifier for Business Impact, this specific case would
    silently produce the wrong answer.
    """
    client = _client_for(_make_handler(business_impact_items=[_business_impact(confidence=raw_confidence)]))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    assert response.json()["businessImpactConfidenceLevel"] == expected_level


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


# --- Step 7.X A-06: dimension + time-window scoped NLP evidence -------------


@pytest.mark.anyio
async def test_nlp_evidence_appears_when_incident_has_a_category_anomaly(override_http_client):
    client = _client_for(_make_handler(anomalies=[_category_anomaly(ANOMALY_ID_1)]))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    nlp_items = [item for item in body["evidence"] if item["source"] == "NLP Intelligence"]
    assert len(nlp_items) == 1
    assert "Payment Issue" in nlp_items[0]["headline"]
    assert "3 enrichment" in nlp_items[0]["detail"]
    assert "negative: 2" in nlp_items[0]["detail"]
    # No complaint_id/complaint-level relationship is ever fabricated.
    assert "complaint_id" not in nlp_items[0]["id"]
    assert "complaint" not in nlp_items[0]["detail"].lower()


@pytest.mark.anyio
async def test_nlp_evidence_omitted_when_no_category_dimension_anomaly_exists(override_http_client):
    """Default fixture anomalies are entity_type='global' -- no real dimension to scope by, so no NLP call is even made."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    body = response.json()
    assert "NLP Intelligence" not in [item["source"] for item in body["evidence"]]
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_nlp_evidence_omitted_on_an_honest_zero_result(override_http_client):
    """A genuine zero-match aggregate is not padded into a fabricated evidence card."""
    client = _client_for(
        _make_handler(
            anomalies=[_category_anomaly(ANOMALY_ID_1)],
            nlp_summary=_enrichment_summary(total_count=0, sentiment_counts={}),
        )
    )
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    body = response.json()
    assert "NLP Intelligence" not in [item["source"] for item in body["evidence"]]
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_nlp_evidence_failure_degrades_with_a_warning_not_a_total_failure(override_http_client):
    client = _client_for(_make_handler(anomalies=[_category_anomaly(ANOMALY_ID_1)], nlp_summary_status=503))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert "NLP Intelligence" not in [item["source"] for item in body["evidence"]]
    assert any("NLP enrichment summary" in warning for warning in body["warnings"])
    # The rest of the Investigation still renders.
    assert body["rootCause"] is not None


@pytest.mark.anyio
async def test_nlp_evidence_query_uses_the_anomalys_own_real_category_and_detection_window(override_http_client):
    captured: list = []
    client = _client_for(
        _make_handler(
            anomalies=[_category_anomaly(ANOMALY_ID_1, entity_value="delivery_issue")],
            captured_nlp_params=captured,
        )
    )
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0]["issue_category"] == "delivery_issue"
    assert captured[0]["start_date"] == "2026-08-08T00:00:00Z"
    assert captured[0]["end_date"] == "2026-08-08T00:30:00Z"


@pytest.mark.anyio
async def test_nlp_evidence_selects_the_alphabetically_first_category_deterministically(override_http_client):
    client = _client_for(
        _make_handler(
            anomalies=[
                _category_anomaly(ANOMALY_ID_1, entity_value="payment_issue"),
                _category_anomaly(ANOMALY_ID_2, entity_value="delivery_issue"),
            ],
            nlp_summary=_enrichment_summary(issue_category="delivery_issue"),
        )
    )
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    body = response.json()
    nlp_items = [item for item in body["evidence"] if item["source"] == "NLP Intelligence"]
    assert len(nlp_items) == 1
    assert "Delivery Issue" in nlp_items[0]["headline"]  # "delivery_issue" sorts before "payment_issue"


# ---------------------------------------------------------------------------
# Phase 13 Batch 8: Investigation Aggregator concurrency fix.
#
# Deterministic proof via `asyncio.Event`, never wall-clock timing (a slow
# CI machine must never make these tests flaky, and a fast one must never
# make them falsely pass a still-sequential implementation). Each test
# below constructs a scenario that can only complete successfully if two
# downstream fetches are genuinely running concurrently -- if the
# aggregator regressed to sequential fetching, the blocked handler would
# hang until its own `asyncio.wait_for` timeout fires, surfacing as a
# real request failure the test's own status-code assertion catches.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_incident_and_root_cause_fetches_run_concurrently(override_http_client):
    """
    The exact defect this batch fixes (§29): Root Cause's fetch depends
    only on `incident_id`, never on the *returned* Incident data, so it
    must not wait for the Incident fetch to finish. Proven here by
    having the Incident handler block until the Root Cause handler has
    already started -- impossible under the old sequential
    implementation, where Root Cause was never even requested until
    Incident's own `await` had already returned.
    """
    root_cause_started = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith(f"/incidents/{INCIDENT_ID}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            await asyncio.wait_for(root_cause_started.wait(), timeout=2)
            return _json(_incident())
        if path.endswith("/root-cause"):
            root_cause_started.set()
            return _json(_root_cause())
        if path.endswith("/anomalies"):
            return _json([])
        if path.endswith("/business-impact"):
            return _json([])
        if path.endswith("/recommendations/latest"):
            return _json([])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200


@pytest.mark.anyio
async def test_all_five_downstream_fetches_start_before_any_of_them_resolves(override_http_client):
    """
    Broader proof than the incident/root-cause pair alone: every one of
    the five real downstream calls (Incident, Root Cause, Anomalies,
    Business Impact, Recommendation) must have been *issued* before any
    of them is allowed to complete -- proven with a shared barrier
    `asyncio.Event` that only fires once all five handlers have recorded
    their own start, which every handler then waits on before returning.
    A still-sequential implementation would deadlock (each call started
    only after the previous one's response arrives) and hit the
    `wait_for` timeout below.
    """
    started = set()
    all_started = asyncio.Event()

    async def _mark_started_and_wait(name: str) -> None:
        started.add(name)
        if len(started) == 5:
            all_started.set()
        await asyncio.wait_for(all_started.wait(), timeout=2)

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith(f"/incidents/{INCIDENT_ID}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            await _mark_started_and_wait("incident")
            return _json(_incident())
        if path.endswith("/root-cause"):
            await _mark_started_and_wait("root_cause")
            return _json(_root_cause())
        if path.endswith("/anomalies"):
            await _mark_started_and_wait("anomalies")
            return _json([])
        if path.endswith("/business-impact"):
            await _mark_started_and_wait("business_impact")
            return _json([])
        if path.endswith("/recommendations/latest"):
            await _mark_started_and_wait("recommendation")
            return _json([])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    assert started == {"incident", "root_cause", "anomalies", "business_impact", "recommendation"}


@pytest.mark.anyio
async def test_incident_failure_does_not_leak_an_unretrieved_task_exception(override_http_client, recwarn):
    """
    When the essential Incident fetch fails, the concurrently-started
    Root Cause/Anomalies/Business Impact/Recommendation tasks must be
    cancelled and drained (`_cancel_and_drain`), not merely abandoned --
    otherwise a task holding an exception (Business Impact 503 here)
    would later be garbage-collected with its exception never retrieved.
    Response correctness is the primary assertion; `recwarn` additionally
    guards against a `RuntimeWarning`/`pytest.PytestUnraisableExceptionWarning`
    surfacing from a dangling task during this test's own teardown.
    """
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith(f"/incidents/{INCIDENT_ID}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            return httpx.Response(404)
        if path.endswith("/root-cause"):
            return _json(_root_cause())
        if path.endswith("/anomalies"):
            return _json([])
        if path.endswith("/business-impact"):
            # A concurrently-started task that would hold an unretrieved
            # exception if the essential-failure cleanup didn't drain it.
            return httpx.Response(503)
        if path.endswith("/recommendations/latest"):
            return _json([])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # Give the event loop one more turn so a truly-dangling task's
    # "exception never retrieved" callback (fired by the loop's default
    # exception handler on next iteration/GC) would have already run.
    await asyncio.sleep(0)
    assert not any(issubclass(w.category, RuntimeWarning) for w in recwarn.list)


@pytest.mark.anyio
async def test_root_cause_essential_failure_still_cancels_the_remaining_non_essential_tasks(override_http_client):
    """Same cleanup guarantee as the incident-failure path above, for Root Cause's own essential-if-erroring failure."""
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith(f"/incidents/{INCIDENT_ID}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            return _json(_incident())
        if path.endswith("/root-cause"):
            return httpx.Response(503)
        if path.endswith("/anomalies"):
            return _json([])
        if path.endswith("/business-impact"):
            return httpx.Response(503)
        if path.endswith("/recommendations/latest"):
            return _json([])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"


@pytest.mark.anyio
async def test_concurrent_downstream_completion_order_does_not_affect_the_response(override_http_client):
    """
    No race condition regardless of which downstream call resolves
    first: Root Cause is made to resolve before Incident here (the
    reverse of natural request order), and the response must still be
    identical to the default-ordering case.
    """
    incident_may_resolve = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith(f"/incidents/{INCIDENT_ID}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            await asyncio.wait_for(incident_may_resolve.wait(), timeout=2)
            return _json(_incident())
        if path.endswith("/root-cause"):
            incident_may_resolve.set()
            return _json(_root_cause())
        if path.endswith("/anomalies"):
            return _json([_anomaly(ANOMALY_ID_1), _anomaly(ANOMALY_ID_2)])
        if path.endswith("/business-impact"):
            return _json([_business_impact()])
        if path.endswith("/recommendations/latest"):
            return _json([_recommendation()])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(f"/api/v1/investigations/{INCIDENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["incidentId"] == INCIDENT_ID
    assert body["rootCause"]["confidenceLevel"] == "high"
    assert body["recommendedNextStep"]["recommendationId"] == RECOMMENDATION_ID
    assert body["warnings"] == []


@pytest.mark.anyio
async def test_request_id_survives_concurrent_downstream_fetches(override_http_client):
    """Correlation ID propagation (Phase 11) is unaffected by running Incident/Root Cause/etc. concurrently instead of sequentially."""
    client = _client_for(_make_handler())
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.get(
            f"/api/v1/investigations/{INCIDENT_ID}", headers={"X-Request-ID": "test-investigation-request-id"}
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-investigation-request-id"


@pytest.mark.anyio
async def test_two_concurrent_investigation_requests_do_not_cross_contaminate_request_ids(override_http_client):
    """
    Two genuinely concurrent Investigation requests (different incidents,
    different X-Request-ID values, in flight at the same time) must each
    receive their own correlation ID back -- proves per-request state
    (request ID, and by extension each request's own task set) is never
    accidentally shared as mutable module/global state.
    """
    other_incident_id = str(uuid.uuid4())
    release = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith(f"/incidents/{INCIDENT_ID}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            await asyncio.wait_for(release.wait(), timeout=2)
            return _json(_incident())
        if path.endswith(f"/incidents/{other_incident_id}") and settings.ANOMALY_SERVICE_URL in str(request.url):
            release.set()
            return _json({**_incident(), "id": other_incident_id})
        if path.endswith("/root-cause"):
            return httpx.Response(404)
        if path.endswith("/anomalies"):
            return _json([])
        if path.endswith("/business-impact"):
            return _json([])
        if path.endswith("/recommendations/latest"):
            return _json([])
        raise AssertionError(f"Unexpected downstream call: {request.url}")

    client = _client_for(handler)
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        first_request = test_client.get(
            f"/api/v1/investigations/{INCIDENT_ID}", headers={"X-Request-ID": "request-a"}
        )
        second_request = test_client.get(
            f"/api/v1/investigations/{other_incident_id}", headers={"X-Request-ID": "request-b"}
        )
        first_response, second_response = await asyncio.gather(first_request, second_request)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.headers["X-Request-ID"] == "request-a"
    assert second_response.headers["X-Request-ID"] == "request-b"
    assert first_response.json()["incidentId"] == INCIDENT_ID
    assert second_response.json()["incidentId"] == other_incident_id


# ---------------------------------------------------------------------------
# Root-cause lifecycle actions (confirm/reject/refresh) -- previously a real
# root_cause_service capability with no Gateway route at all.
# ---------------------------------------------------------------------------

ROOT_CAUSE_ID = str(uuid.uuid4())


def _root_cause_action_handler(*, lookup_status=200, action_status=200, action_body=None):
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path.endswith("/root-cause"):
            if lookup_status == 404:
                return httpx.Response(404)
            if lookup_status != 200:
                return httpx.Response(lookup_status)
            return _json({**_root_cause(), "id": ROOT_CAUSE_ID})

        if f"/root-causes/{ROOT_CAUSE_ID}" in path:
            if action_status != 200:
                return httpx.Response(action_status)
            body = action_body if action_body is not None else {**_root_cause(), "id": ROOT_CAUSE_ID, "status": "confirmed"}
            return _json(body)

        raise AssertionError(f"Unexpected downstream call: {request.url}")

    return handler


@pytest.mark.anyio
async def test_confirm_root_cause_resolves_id_by_incident_then_confirms_it(override_http_client):
    client = _client_for(_root_cause_action_handler(action_body={**_root_cause(), "id": ROOT_CAUSE_ID, "status": "confirmed"}))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(f"/api/v1/investigations/{INCIDENT_ID}/root-cause/confirm")

    assert response.status_code == 200
    body = response.json()
    assert body["incidentId"] == INCIDENT_ID
    assert body["status"] == "confirmed"


@pytest.mark.anyio
async def test_reject_root_cause_resolves_id_by_incident_then_rejects_it(override_http_client):
    client = _client_for(_root_cause_action_handler(action_body={**_root_cause(), "id": ROOT_CAUSE_ID, "status": "rejected"}))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(f"/api/v1/investigations/{INCIDENT_ID}/root-cause/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.anyio
async def test_refresh_root_cause_resolves_id_by_incident_then_refreshes_it(override_http_client):
    client = _client_for(_root_cause_action_handler(action_body={**_root_cause(), "id": ROOT_CAUSE_ID, "status": "identified"}))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.post(f"/api/v1/investigations/{INCIDENT_ID}/root-cause/refresh")

    assert response.status_code == 200
    assert response.json()["status"] == "identified"


@pytest.mark.anyio
async def test_confirm_root_cause_when_none_exists_yet_is_a_real_404(override_http_client):
    client = _client_for(_root_cause_action_handler(lookup_status=404))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(f"/api/v1/investigations/{INCIDENT_ID}/root-cause/confirm")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_confirm_root_cause_invalid_transition_is_a_real_409_not_a_502(override_http_client):
    """root_cause_service's own 409 (e.g. confirming an already-rejected RootCause) must survive as a real Gateway conflict."""
    client = _client_for(_root_cause_action_handler(action_status=409))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(f"/api/v1/investigations/{INCIDENT_ID}/root-cause/confirm")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.anyio
async def test_reject_root_cause_downstream_failure_maps_to_502(override_http_client):
    client = _client_for(_root_cause_action_handler(action_status=500))
    override_http_client(client)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as test_client:
        response = await test_client.patch(f"/api/v1/investigations/{INCIDENT_ID}/root-cause/reject")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DOWNSTREAM_SERVICE_FAILURE"
