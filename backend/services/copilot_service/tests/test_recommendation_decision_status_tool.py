import httpx
import pytest

from backend.services.copilot_service.app.schemas.tools import RecommendationDecisionStatusInput
from backend.services.copilot_service.app.services import recommendation_decision_status_tool as tool

RECOMMENDATION_ID = "11111111-1111-1111-1111-111111111111"


def _payload(**overrides):
    payload = {
        "recommendation_id": RECOMMENDATION_ID,
        "incident_id": "incident-42",
        "generation_id": "22222222-2222-2222-2222-222222222222",
        "category": "escalate",
        "priority": "high",
        "score": 88,
        "action": "Escalate to payments team",
        "recommendation_rationale": "x",
        "priority_rationale": "y",
        "supporting_evidence": [],
        "created_at": "2026-08-08T01:05:00Z",
        "decision": None,
        "decision_note": None,
        "decided_at": None,
    }
    payload.update(overrides)
    return payload


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_pending_decision_reports_none_not_a_fabricated_value():
    client = _client_for(lambda request: httpx.Response(200, json=_payload()))
    result = await tool.run(client, RecommendationDecisionStatusInput(recommendation_id=RECOMMENDATION_ID))

    assert result.found is True
    assert result.decision is None
    assert result.decided_at is None
    assert result.evidence_references == []  # no decision timestamp yet -- no evidence to cite


@pytest.mark.anyio
async def test_real_decision_fields_are_reported():
    payload = _payload(decision="approved", decision_note="Reviewed and approved.", decided_at="2026-08-12T10:00:00Z")
    client = _client_for(lambda request: httpx.Response(200, json=payload))
    result = await tool.run(client, RecommendationDecisionStatusInput(recommendation_id=RECOMMENDATION_ID))

    assert result.decision == "approved"
    assert result.decision_note == "Reviewed and approved."
    assert result.decided_at == "2026-08-12T10:00:00Z"
    assert len(result.evidence_references) == 1
    assert result.evidence_references[0].timestamp == "2026-08-12T10:00:00Z"


@pytest.mark.anyio
async def test_missing_recommendation_is_a_legitimate_absence():
    client = _client_for(lambda request: httpx.Response(404))
    result = await tool.run(client, RecommendationDecisionStatusInput(recommendation_id=RECOMMENDATION_ID))

    assert result.found is False
    assert result.error is None


def test_this_tool_never_calls_a_mutating_http_method():
    """
    Structural check: the module must never invoke `.patch(`/`.post(`/
    `.put(`/`.delete(` on the HTTP client, and must only import the
    read-only `get_json` helper (`core/downstream.py` exposes no
    mutating verb at all -- see test_tool_registry.py's own check).
    """
    import inspect

    source = inspect.getsource(tool)
    for forbidden in (".patch(", ".post(", ".put(", ".delete(", "patch_json", "post_json"):
        assert forbidden not in source
