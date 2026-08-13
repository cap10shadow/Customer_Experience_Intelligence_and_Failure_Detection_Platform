import httpx
import pytest

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.schemas.tools import InvestigationToolInput
from backend.services.copilot_service.app.services import investigation_tool as tool

INCIDENT_ID = "incident-42"

_ANOMALY_PORT = httpx.URL(settings.ANOMALY_SERVICE_URL).port
_ROOT_CAUSE_PORT = httpx.URL(settings.ROOT_CAUSE_SERVICE_URL).port
_BUSINESS_IMPACT_PORT = httpx.URL(settings.BUSINESS_IMPACT_SERVICE_URL).port
_RECOMMENDATION_PORT = httpx.URL(settings.RECOMMENDATION_SERVICE_URL).port
_NLP_PORT = httpx.URL(settings.NLP_SERVICE_URL).port


def _incident_payload():
    return {
        "id": INCIDENT_ID,
        "incident_key": "INC-42",
        "title": "Payment failures spike",
        "severity": "critical",
        "status": "active",
        "confidence_score": 90,
        "summary": "A spike in payment failures was detected.",
        "started_at": "2026-08-08T00:00:00Z",
        "last_updated_at": "2026-08-08T00:05:00Z",
        "resolved_at": None,
    }


def _anomaly_payload(entity_type="category", entity_value="billing"):
    return {
        "id": "anomaly-1",
        "type": "spike",
        "severity": "critical",
        "entity_type": entity_type,
        "entity_value": entity_value,
        "explanation": "An anomaly was detected.",
        "triggered_rule": "z_score",
        "first_detected_at": "2026-08-08T00:00:00Z",
        "last_seen_at": "2026-08-08T00:04:00Z",
    }


def _default_handler(request: httpx.Request) -> httpx.Response:
    port = request.url.port
    path = request.url.path
    if port == _ANOMALY_PORT and path == f"/api/v1/incidents/{INCIDENT_ID}":
        return httpx.Response(200, json=_incident_payload())
    if port == _ANOMALY_PORT and path == f"/api/v1/incidents/{INCIDENT_ID}/anomalies":
        return httpx.Response(200, json=[])
    if port == _ROOT_CAUSE_PORT:
        return httpx.Response(404)
    if port == _BUSINESS_IMPACT_PORT:
        return httpx.Response(200, json=[])
    if port == _RECOMMENDATION_PORT:
        return httpx.Response(200, json=[])
    if port == _NLP_PORT:
        return httpx.Response(200, json={"issue_category": "billing", "total_count": 0, "sentiment_counts": {}})
    raise AssertionError(f"unexpected request: {request.url}")


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_incident_not_found_is_a_legitimate_absence():
    client = _client_for(lambda request: httpx.Response(404))
    result = await tool.run(client, InvestigationToolInput(incident_id=INCIDENT_ID))

    assert result.found is False
    assert result.error is None


@pytest.mark.anyio
async def test_incident_service_unreachable_is_a_structured_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_for(handler)
    result = await tool.run(client, InvestigationToolInput(incident_id=INCIDENT_ID))

    assert result.found is False
    assert result.error is not None


@pytest.mark.anyio
async def test_minimal_successful_investigation_returns_the_real_incident():
    client = _client_for(_default_handler)
    result = await tool.run(client, InvestigationToolInput(incident_id=INCIDENT_ID))

    assert result.found is True
    assert result.incident.title == "Payment failures spike"
    assert result.root_cause is None  # legitimate absence (404) -- no limitation recorded
    assert result.business_impact is None
    assert result.latest_recommendations == []
    assert "Root cause data for this incident is temporarily unavailable." not in result.limitations


@pytest.mark.anyio
async def test_degraded_source_produces_an_honest_limitation_not_a_fabricated_gap():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port == _BUSINESS_IMPACT_PORT:
            raise httpx.TimeoutException("timed out", request=request)
        return _default_handler(request)

    client = _client_for(handler)
    result = await tool.run(client, InvestigationToolInput(incident_id=INCIDENT_ID))

    assert result.found is True  # the incident itself still succeeded
    assert result.business_impact is None
    assert any("Business impact" in limitation for limitation in result.limitations)


@pytest.mark.anyio
async def test_category_anomaly_triggers_a_scoped_nlp_lookup():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port == _ANOMALY_PORT and request.url.path == f"/api/v1/incidents/{INCIDENT_ID}/anomalies":
            return httpx.Response(200, json=[_anomaly_payload()])
        if request.url.port == _NLP_PORT:
            assert request.url.params["issue_category"] == "billing"
            return httpx.Response(200, json={"issue_category": "billing", "total_count": 3, "sentiment_counts": {"negative": 3}})
        return _default_handler(request)

    client = _client_for(handler)
    result = await tool.run(client, InvestigationToolInput(incident_id=INCIDENT_ID))

    assert len(result.anomalies) == 1
    assert result.nlp_summary is not None
    assert result.nlp_summary.total_count == 3


@pytest.mark.anyio
async def test_no_category_anomaly_means_no_nlp_lookup_is_attempted():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.port)
        if request.url.port == _ANOMALY_PORT and request.url.path == f"/api/v1/incidents/{INCIDENT_ID}/anomalies":
            return httpx.Response(200, json=[_anomaly_payload(entity_type="region", entity_value="west")])
        return _default_handler(request)

    client = _client_for(handler)
    result = await tool.run(client, InvestigationToolInput(incident_id=INCIDENT_ID))

    assert result.nlp_summary is None
    assert _NLP_PORT not in calls


@pytest.mark.anyio
async def test_evidence_references_are_collected_across_sources():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port == _ROOT_CAUSE_PORT:
            return httpx.Response(
                200,
                json={
                    "id": "root-cause-1",
                    "incident_id": INCIDENT_ID,
                    "cause": "service_outage",
                    "confidence_score": 85,
                    "confidence_level": "High",
                    "evidence": [],
                    "explanation": "x",
                    "rule_version": "v1",
                    "status": "unconfirmed",
                    "created_at": "2026-08-08T00:00:00Z",
                    "updated_at": "2026-08-08T00:05:00Z",
                },
            )
        return _default_handler(request)

    client = _client_for(handler)
    result = await tool.run(client, InvestigationToolInput(incident_id=INCIDENT_ID))

    source_types = {e.source_type for e in result.evidence_references}
    assert "incident" in source_types
    assert "root_cause" in source_types
