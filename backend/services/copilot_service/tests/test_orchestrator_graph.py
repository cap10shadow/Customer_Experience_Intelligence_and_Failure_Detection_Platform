"""
Tests for the Phase 12 Batch 3 LangGraph orchestration graph
(orchestrator/graph.py). A deterministic `FakeLLMProvider` (scripted
decisions, never a live API call) stands in for the LLM throughout --
per the Batch 3 implementation prompt §33, the regression suite must
never depend on a live provider/API key. `build_graph()` is called
directly (the same injectable-provider entry point the architecture's
adapter boundary exists to support), not the higher-level
`orchestrator_service.run_orchestration` (which selects a provider via
environment configuration).
"""

from typing import List

import httpx
import pytest

from backend.services.copilot_service.app.services import tools_bootstrap  # noqa: F401 -- registers all 7 tools
from backend.services.copilot_service.app.services.orchestrator.graph import MAX_EVIDENCE_ITEMS, build_graph
from backend.services.copilot_service.app.services.orchestrator.state import (
    MAX_TOOL_ROUNDS,
    Decision,
    FinalAnswerDecision,
    OrchestrationState,
    ToolCallDecision,
)

RECOMMENDATION_ID = "11111111-1111-1111-1111-111111111111"


class FakeLLMProvider:
    """Returns a pre-scripted sequence of decisions, ignoring the prompt entirely -- deterministic by construction."""

    def __init__(self, decisions: List[Decision]) -> None:
        self._decisions = list(decisions)
        self.calls = 0

    async def decide(self, *, messages, available_tools):
        self.calls += 1
        if not self._decisions:
            raise AssertionError("FakeLLMProvider was called more times than scripted -- iteration bound was not enforced.")
        return self._decisions.pop(0)


def _recommendation_payload(**overrides):
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


def _initial_state(message: str = "hello") -> OrchestrationState:
    return {
        "message": message,
        "workspace_context": None,
        "conversation_id": "conv-1",
        "request_id": "req-1",
        "rounds_used": 0,
        "tool_calls_made": [],
        "seen_calls": [],
        "evidence_references": [],
        "limitations": [],
        "last_decision": None,
        "final_answer": None,
    }


def _client_for(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_immediate_final_answer_makes_no_tool_call():
    calls = []
    client = _client_for(lambda r: calls.append(r) or httpx.Response(200, json={}))
    provider = FakeLLMProvider([FinalAnswerDecision(answer="No tool needed.")])
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert calls == []
    assert result["final_answer"].answer == "No tool needed."
    assert result["rounds_used"] == 0


@pytest.mark.anyio
async def test_valid_tool_call_produces_real_grounded_evidence():
    payload = _recommendation_payload(decision="approved", decided_at="2026-08-12T10:00:00Z")
    client = _client_for(lambda r: httpx.Response(200, json=payload))
    provider = FakeLLMProvider(
        [
            ToolCallDecision("recommendation_decision_status", {"recommendation_id": RECOMMENDATION_ID}),
            FinalAnswerDecision(answer="It was approved.", evidence_ids=[]),
        ]
    )
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert result["rounds_used"] == 1
    assert len(result["tool_calls_made"]) == 1
    assert result["tool_calls_made"][0].succeeded is True
    assert len(result["evidence_references"]) == 1


@pytest.mark.anyio
async def test_iteration_budget_is_enforced_structurally():
    """The provider keeps requesting a (valid) tool call forever -- the graph must still stop at MAX_TOOL_ROUNDS."""
    client = _client_for(lambda r: httpx.Response(404))
    infinite_tool_calls = [ToolCallDecision("recommendation_decision_status", {"recommendation_id": RECOMMENDATION_ID})] * 10
    provider = FakeLLMProvider(infinite_tool_calls)
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert result["rounds_used"] == MAX_TOOL_ROUNDS
    assert provider.calls == MAX_TOOL_ROUNDS  # never consulted a 4th time
    assert len(result["tool_calls_made"]) == MAX_TOOL_ROUNDS
    assert result["final_answer"] is not None  # a forced wrap-up was produced, not a crash


@pytest.mark.anyio
async def test_duplicate_tool_call_is_not_re_executed():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(200, json=_recommendation_payload())

    client = _client_for(handler)
    same_call = ToolCallDecision("recommendation_decision_status", {"recommendation_id": RECOMMENDATION_ID})
    provider = FakeLLMProvider([same_call, same_call, FinalAnswerDecision(answer="done")])
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert call_count["n"] == 1  # the real HTTP call happened exactly once
    assert any(r.skipped_reason == "duplicate_call" for r in result["tool_calls_made"])


@pytest.mark.anyio
async def test_unknown_tool_name_is_never_executed():
    calls = []
    client = _client_for(lambda r: calls.append(r) or httpx.Response(200, json={}))
    provider = FakeLLMProvider(
        [ToolCallDecision("delete_everything", {}), FinalAnswerDecision(answer="Could not do that.")]
    )
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert calls == []  # no HTTP call was ever made for the unknown tool
    assert any(r.skipped_reason == "unknown_tool" for r in result["tool_calls_made"])
    assert any("unavailable tool" in limitation for limitation in result["limitations"])


@pytest.mark.anyio
async def test_invalid_tool_arguments_are_rejected_before_execution():
    calls = []
    client = _client_for(lambda r: calls.append(r) or httpx.Response(200, json={}))
    # root_cause requires incident_id or root_cause_id -- neither is
    # itself a schema violation, so use a genuinely malformed field
    # (extra="forbid" on RootCauseToolInput) to trigger real validation failure.
    provider = FakeLLMProvider(
        [
            ToolCallDecision("root_cause", {"not_a_real_field": "x"}),
            FinalAnswerDecision(answer="Could not look that up."),
        ]
    )
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert calls == []
    assert any(r.skipped_reason == "invalid_arguments" for r in result["tool_calls_made"])


@pytest.mark.anyio
async def test_model_claimed_evidence_id_that_does_not_exist_is_dropped():
    client = _client_for(lambda r: httpx.Response(200, json=_recommendation_payload()))
    real_evidence_id = f"recommendation:{RECOMMENDATION_ID}"
    provider = FakeLLMProvider(
        [
            ToolCallDecision("recommendation_decision_status", {"recommendation_id": RECOMMENDATION_ID}),
            FinalAnswerDecision(
                answer="Decided.",
                evidence_ids=[real_evidence_id, "recommendation:invented-id-that-was-never-returned"],
            ),
        ]
    )
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    # recommendation_decision_status only produces an evidence reference
    # when decided_at is present (see recommendation_decision_status_tool.py) --
    # this fixture has decided_at=None, so no real evidence exists at all,
    # meaning *both* claimed IDs must be dropped.
    from backend.services.copilot_service.app.services.orchestrator.synthesis import synthesize_response

    response = synthesize_response(result)
    assert response.evidence_references == []


@pytest.mark.anyio
async def test_real_evidence_is_preserved_and_invented_id_is_dropped():
    payload = _recommendation_payload(decision="approved", decision_note="ok", decided_at="2026-08-12T10:00:00Z")
    client = _client_for(lambda r: httpx.Response(200, json=payload))
    real_evidence_id = f"recommendation_decision:{RECOMMENDATION_ID}"
    provider = FakeLLMProvider(
        [
            ToolCallDecision("recommendation_decision_status", {"recommendation_id": RECOMMENDATION_ID}),
            FinalAnswerDecision(
                answer="This recommendation was approved.",
                evidence_ids=[real_evidence_id, "recommendation:totally-invented"],
            ),
        ]
    )
    graph = build_graph(provider, client)
    result = await graph.ainvoke(_initial_state())

    from backend.services.copilot_service.app.services.orchestrator.synthesis import synthesize_response

    response = synthesize_response(result)
    cited_ids = {e.evidence_id for e in response.evidence_references}
    assert cited_ids == {real_evidence_id}


@pytest.mark.anyio
async def test_llm_failure_preserves_already_gathered_evidence():
    from backend.services.copilot_service.app.services.orchestrator.llm_provider import LLMProviderError

    class _FailingAfterOneCall:
        def __init__(self):
            self.calls = 0

        async def decide(self, *, messages, available_tools):
            self.calls += 1
            if self.calls == 1:
                return ToolCallDecision("recommendation_decision_status", {"recommendation_id": RECOMMENDATION_ID})
            raise LLMProviderError("simulated provider outage")

    payload = _recommendation_payload(decided_at="2026-08-12T10:00:00Z")
    client = _client_for(lambda r: httpx.Response(200, json=payload))
    provider = _FailingAfterOneCall()
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert len(result["evidence_references"]) == 1  # not lost despite the provider failure
    assert result["final_answer"] is not None
    assert any(
        "provider" in limitation.lower() or "unavailable" in limitation.lower()
        for limitation in result["final_answer"].limitations
    )


@pytest.mark.anyio
async def test_evidence_item_cap_is_enforced():
    """MAX_EVIDENCE_ITEMS bounds total evidence regardless of how many a single tool call returns."""
    incident_payload = {
        "id": "incident-1",
        "incident_key": "INC-1",
        "title": "t",
        "severity": "high",
        "status": "active",
        "confidence_score": 50,
        "summary": "s",
        "started_at": "2026-08-08T00:00:00Z",
        "last_updated_at": "2026-08-08T00:00:00Z",
        "resolved_at": None,
    }
    many_anomalies = [
        {
            "id": f"anomaly-{i}",
            "type": "spike",
            "severity": "high",
            "entity_type": "region",
            "entity_value": "west",
            "explanation": "x",
            "triggered_rule": "r",
            "first_detected_at": "2026-08-08T00:00:00Z",
            "last_seen_at": "2026-08-08T00:00:00Z",
        }
        for i in range(MAX_EVIDENCE_ITEMS + 10)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/incidents/incident-1":
            return httpx.Response(200, json=incident_payload)
        if request.url.path == "/api/v1/incidents/incident-1/anomalies":
            return httpx.Response(200, json=many_anomalies)
        return httpx.Response(404)

    client = _client_for(handler)
    provider = FakeLLMProvider(
        [ToolCallDecision("investigation", {"incident_id": "incident-1"}), FinalAnswerDecision(answer="done")]
    )
    graph = build_graph(provider, client)

    result = await graph.ainvoke(_initial_state())

    assert len(result["evidence_references"]) <= MAX_EVIDENCE_ITEMS
