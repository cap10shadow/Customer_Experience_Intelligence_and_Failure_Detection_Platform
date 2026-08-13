import httpx
import pytest

from backend.services.copilot_service.app.schemas.tools import BusinessImpactToolInput
from backend.services.copilot_service.app.services import business_impact_tool as tool

ASSESSMENT_ID = "44444444-4444-4444-4444-444444444444"
INCIDENT_ID = "incident-42"


def _payload(**overrides):
    payload = {
        "assessment_id": ASSESSMENT_ID,
        "incident_id": INCIDENT_ID,
        "root_cause_id": "33333333-3333-3333-3333-333333333333",
        "financial": "high",
        "customer": "medium",
        "operational": "critical",
        "sla": "low",
        "reputation": "none",
        "overall_score": 78,
        "overall_severity": "high",
        "business_priority": "high",
        "confidence": 80,
        "estimated_affected_customers": 250,
        "explanation": "Overall business impact is high.",
        "status": "active",
        "created_at": "2026-08-08T00:00:00Z",
        "updated_at": "2026-08-08T00:10:00Z",
    }
    payload.update(overrides)
    return payload


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_lookup_by_incident_id_uses_the_query_filter_and_takes_the_first_result():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/business-impact"
        assert request.url.params["incident_id"] == INCIDENT_ID
        return httpx.Response(200, json=[_payload()])

    client = _client_for(handler)
    result = await tool.run(client, BusinessImpactToolInput(incident_id=INCIDENT_ID))

    assert result.found is True
    assert result.assessment.overall_score == 78
    assert result.assessment.confidence == 80  # ARB-008: this is BI's own stage-specific confidence


@pytest.mark.anyio
async def test_lookup_by_assessment_id_calls_the_direct_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/business-impact/{ASSESSMENT_ID}"
        return httpx.Response(200, json=_payload())

    client = _client_for(handler)
    result = await tool.run(client, BusinessImpactToolInput(assessment_id=ASSESSMENT_ID))

    assert result.found is True


@pytest.mark.anyio
async def test_no_assessment_yet_is_a_legitimate_absence():
    client = _client_for(lambda request: httpx.Response(200, json=[]))
    result = await tool.run(client, BusinessImpactToolInput(incident_id=INCIDENT_ID))

    assert result.found is False
    assert result.error is None


@pytest.mark.anyio
async def test_downstream_failure_is_a_structured_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client = _client_for(handler)
    result = await tool.run(client, BusinessImpactToolInput(incident_id=INCIDENT_ID))

    assert result.found is False
    assert result.error is not None


def test_no_mutation_endpoint_is_referenced_anywhere_in_this_module():
    import inspect

    source = inspect.getsource(tool)
    for forbidden in ("patch(", "post(", "PATCH", "delete("):
        assert forbidden not in source
