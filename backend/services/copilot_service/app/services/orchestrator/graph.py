"""
Phase 12 Batch 3 -- the LangGraph orchestration graph (architecture §20):

    Question -> Tool decision -> Tool call -> Evidence -> Optional next
    tool (<=3 rounds) -> Answer

LangGraph here is purely the bounded state machine described above --
it never recreates any domain workflow (NLP/Anomaly/Incident/Root-Cause/
Business-Impact/Recommendation all remain owned by their existing
services, entirely untouched by this graph). No checkpointer is
configured: `StateGraph(...).compile()` below runs fully in-memory for
the duration of one request and persists nothing (Phase 12 architecture
§24 -- conversation persistence is explicitly Batch 4, not this batch).
"""

import json
from typing import Any, Dict, List

import httpx
from langgraph.graph import END, StateGraph

from backend.services.copilot_service.app.services.orchestrator.llm_provider import LLMProvider, LLMProviderError
from backend.services.copilot_service.app.services.orchestrator.prompts import build_messages, tool_specs_for_llm
from backend.services.copilot_service.app.services.orchestrator.state import (
    MAX_TOOL_ROUNDS,
    FinalAnswerDecision,
    OrchestrationState,
    ToolCallDecision,
    ToolCallRecord,
)
from backend.services.copilot_service.app.services.tool_registry import UnknownToolError, call_tool, list_tools

# Bounds (architecture §19 -- "total tool execution time, total evidence
# item count, individual result size, conversation context size... must
# exist, per this invariant, before Batch 3 ships"). MAX_TOOL_ROUNDS is
# frozen by the architecture itself; the others are this batch's own
# implementation-time configuration decision, applied structurally below.
TOOL_CALL_TIMEOUT_SECONDS = 10.0
MAX_EVIDENCE_ITEMS = 20


def _canonical_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    return f"{tool_name}:{json.dumps(arguments, sort_keys=True, default=str)}"


def build_graph(llm_provider: LLMProvider, client: httpx.AsyncClient):
    graph = StateGraph(OrchestrationState)

    async def decide_node(state: OrchestrationState) -> OrchestrationState:
        rounds_used = state.get("rounds_used", 0)
        if rounds_used >= MAX_TOOL_ROUNDS:
            # Structural stop: the LLM is never even asked again once the
            # budget is exhausted -- no request can bypass this by
            # repeatedly asking for "one more" tool.
            decision: Any = _forced_wrap_up(state, reason="Tool call budget was reached.")
        else:
            tools = tool_specs_for_llm(list_tools())
            messages = build_messages(state)
            try:
                decision = await llm_provider.decide(messages=messages, available_tools=tools)
            except LLMProviderError as exc:
                # LLM failure must not lose evidence already gathered
                # (architecture §22/§23) -- fall back to a deterministic
                # wrap-up using whatever real evidence exists so far.
                decision = _forced_wrap_up(state, reason=f"The language model was unavailable: {exc}.")

        new_state = dict(state)
        new_state["last_decision"] = decision
        if not isinstance(decision, FinalAnswerDecision):
            new_state["rounds_used"] = rounds_used + 1
        return new_state

    async def call_tool_node(state: OrchestrationState) -> OrchestrationState:
        decision = state["last_decision"]
        assert isinstance(decision, ToolCallDecision)

        tool_calls_made: List[ToolCallRecord] = list(state.get("tool_calls_made", []))
        seen_calls: List[str] = list(state.get("seen_calls", []))
        evidence_references = list(state.get("evidence_references", []))
        limitations = list(state.get("limitations", []))

        canonical = _canonical_call(decision.tool_name, decision.arguments)
        if canonical in seen_calls:
            tool_calls_made.append(
                ToolCallRecord(decision.tool_name, decision.arguments, succeeded=False, skipped_reason="duplicate_call")
            )
            limitations.append(f"The tool '{decision.tool_name}' was already called with the same input; skipped.")
        else:
            seen_calls.append(canonical)
            try:
                # Bounded by the shared client's own configured timeout
                # (set once, at client-construction time in
                # orchestrator_service.py -- architecture §19).
                result = await call_tool(decision.tool_name, client, decision.arguments)
            except UnknownToolError:
                tool_calls_made.append(
                    ToolCallRecord(decision.tool_name, decision.arguments, succeeded=False, skipped_reason="unknown_tool")
                )
                limitations.append(f"An unavailable tool ('{decision.tool_name}') was requested and was not called.")
            except Exception as exc:  # noqa: BLE001 -- invalid model-supplied arguments (pydantic ValidationError) or any other construction failure
                tool_calls_made.append(
                    ToolCallRecord(decision.tool_name, decision.arguments, succeeded=False, skipped_reason="invalid_arguments")
                )
                limitations.append(f"The tool '{decision.tool_name}' was called with invalid arguments and was not executed: {type(exc).__name__}.")
            else:
                new_evidence = getattr(result, "evidence_references", [])
                added_ids: List[str] = []
                for item in new_evidence:
                    if len(evidence_references) >= MAX_EVIDENCE_ITEMS:
                        break
                    evidence_references.append(item)
                    added_ids.append(item.evidence_id)
                tool_calls_made.append(
                    ToolCallRecord(
                        decision.tool_name,
                        decision.arguments,
                        succeeded=True,
                        result_evidence_ids=added_ids,
                        result_found=getattr(result, "found", None),
                    )
                )
                result_error = getattr(result, "error", None)
                if result_error is not None:
                    limitations.append(f"The tool '{decision.tool_name}' reported a failure: {result_error}")
                elif hasattr(result, "found") and result.found is False:
                    limitations.append(f"The tool '{decision.tool_name}' found no matching data.")
                for extra_limitation in getattr(result, "limitations", []) or []:
                    limitations.append(extra_limitation)

        new_state = dict(state)
        new_state["tool_calls_made"] = tool_calls_made
        new_state["seen_calls"] = seen_calls
        new_state["evidence_references"] = evidence_references
        new_state["limitations"] = limitations
        return new_state

    async def synthesize_node(state: OrchestrationState) -> OrchestrationState:
        decision = state["last_decision"]
        if not isinstance(decision, FinalAnswerDecision):
            decision = _forced_wrap_up(state, reason="Tool call budget was reached.")
        new_state = dict(state)
        new_state["final_answer"] = decision
        return new_state

    def route_after_decide(state: OrchestrationState) -> str:
        decision = state["last_decision"]
        if isinstance(decision, FinalAnswerDecision):
            return "synthesize"
        return "call_tool"

    graph.add_node("decide", decide_node)
    graph.add_node("call_tool", call_tool_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("decide")
    graph.add_conditional_edges("decide", route_after_decide, {"call_tool": "call_tool", "synthesize": "synthesize"})
    graph.add_edge("call_tool", "decide")
    graph.add_edge("synthesize", END)

    return graph.compile()


def _forced_wrap_up(state: OrchestrationState, *, reason: str) -> FinalAnswerDecision:
    """
    Deterministic, orchestrator-authored fallback -- never calls the LLM
    again. Used both when the round budget is exhausted and when the
    provider itself fails after useful evidence may already exist
    (architecture §22/§23: LLM failure must not lose evidence already
    gathered, and the API contract must never break).
    """
    evidence_count = len(state.get("evidence_references", []))
    if evidence_count > 0:
        answer = (
            f"I gathered {evidence_count} piece(s) of evidence but could not complete a full synthesis "
            f"({reason})."
        )
    else:
        answer = f"I was unable to gather any evidence for this request ({reason})."
    return FinalAnswerDecision(answer=answer, limitations=[reason])
