import httpx
import pytest

from backend.services.copilot_service.app.schemas.tools import RootCauseToolInput
from backend.services.copilot_service.app.services import root_cause_tool as tool

ROOT_CAUSE_ID = "33333333-3333-3333-3333-333333333333"
INCIDENT_ID = "incident-42"


def _payload(**overrides):
    payload = {
        "id": ROOT_CAUSE_ID,
        "incident_id": INCIDENT_ID,
        "cause": "service_outage",
        "confidence_score": 85,
        "confidence_level": "High",
        "evidence": [{"type": "anomaly_correlation", "description": "spike in errors", "weight": 5}],
        "explanation": "service_outage identified with critical anomaly severity",
        "rule_version": "v1",
        "status": "unconfirmed",
        "created_at": "2026-08-08T00:00:00Z",
        "updated_at": "2026-08-08T00:05:00Z",
    }
    payload.update(overrides)
    return payload


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_lookup_by_incident_id_calls_the_incident_scoped_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/incidents/{INCIDENT_ID}/root-cause"
        return httpx.Response(200, json=_payload())

    client = _client_for(handler)
    result = await tool.run(client, RootCauseToolInput(incident_id=INCIDENT_ID))

    assert result.found is True
    assert result.root_cause.cause == "service_outage"
    assert result.root_cause.confidence_score == 85
    assert result.root_cause.evidence[0].description == "spike in errors"


@pytest.mark.anyio
async def test_lookup_by_root_cause_id_calls_the_direct_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/root-causes/{ROOT_CAUSE_ID}"
        return httpx.Response(200, json=_payload())

    client = _client_for(handler)
    result = await tool.run(client, RootCauseToolInput(root_cause_id=ROOT_CAUSE_ID))

    assert result.found is True


@pytest.mark.anyio
async def test_neither_identifier_is_a_structured_error_not_a_downstream_call():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=_payload())

    client = _client_for(handler)
    result = await tool.run(client, RootCauseToolInput())

    assert result.found is False
    assert result.error is not None
    assert calls == []


@pytest.mark.anyio
async def test_not_yet_analyzed_is_a_legitimate_absence():
    client = _client_for(lambda request: httpx.Response(404))
    result = await tool.run(client, RootCauseToolInput(incident_id=INCIDENT_ID))

    assert result.found is False
    assert result.error is None


@pytest.mark.anyio
async def test_evidence_reference_preserves_the_real_root_cause_id_and_timestamp():
    client = _client_for(lambda request: httpx.Response(200, json=_payload()))
    result = await tool.run(client, RootCauseToolInput(incident_id=INCIDENT_ID))

    evidence = result.evidence_references[0]
    assert evidence.source_id == ROOT_CAUSE_ID
    assert evidence.timestamp == "2026-08-08T00:05:00Z"


def test_no_mutation_endpoint_is_called_anywhere_in_this_module():
    """
    Structural check: the module must never invoke `.patch(`/`.post(`/
    `.put(`/`.delete(` on the HTTP client, and must only import the
    read-only `get_json` helper. `confirm`/`reject`/`refresh` are named
    only in this module's own docstring (explaining what is forbidden),
    never constructed as a URL or called as a method.
    """
    import inspect

    source = inspect.getsource(tool)
    for forbidden in (".patch(", ".post(", ".put(", ".delete(", "patch_json", "post_json"):
        assert forbidden not in source, f"unexpected reference to '{forbidden}' in root_cause_tool.py"
