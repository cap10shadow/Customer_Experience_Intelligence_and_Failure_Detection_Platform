from typing import Dict, List, Optional

import httpx

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.orchestrator.graph import build_graph
from backend.services.copilot_service.app.services.orchestrator.llm_provider import LLMProvider, get_llm_provider
from backend.services.copilot_service.app.services.orchestrator.state import OrchestrationState
from backend.services.copilot_service.app.services.orchestrator.synthesis import synthesize_response
from backend.services.copilot_service.app.services import tools_bootstrap  # noqa: F401 -- import-for-registration, see its own docstring


async def run_orchestration(
    request: CopilotQueryRequest,
    *,
    client: httpx.AsyncClient,
    request_id: str,
    conversation_id: str,
    history: Optional[List[Dict[str, str]]] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> CopilotQueryResponse:
    """
    Phase 12 Batch 3 -- runs one bounded orchestration turn (Question ->
    Tool decision -> Tool call -> Evidence -> Optional next tool (<=3
    rounds) -> Answer, architecture §20) and returns the frozen
    `CopilotResponse` shape.

    Phase 12 Batch 4: `conversation_id` resolution (mint-or-reuse) and
    conversation persistence now live one layer up, in
    `services/conversation_service.py` -- `copilot_service` still owns
    conversation identity (COPILOT-002), just no longer inside this
    orchestration-only function. `history` is the bounded, already-
    persisted prior turns for this conversation (oldest first); this
    function does not load or persist anything itself.

    Phase 12 Batch 6: `llm_provider` is an optional override, additive
    and fully backward-compatible -- every existing caller (only
    `conversation_service.handle_persisted_query`) omits it and gets
    exactly today's behavior (`get_llm_provider()`, configuration-driven,
    §24). It exists solely so `app/evaluation/runner.py` can inject a
    deterministic `ScriptedLLMProvider` and exercise this exact real
    orchestration path (graph, tool registry, synthesis, persistence)
    for scenarios (tool selection, conflict disclosure, forbidden-tool
    rejection) that `NullLLMProvider` -- the only provider actually
    configured in this environment -- can never produce on its own,
    since it never calls a tool. This mirrors the same seam
    `build_graph(llm_provider, client)` already exposes one layer down;
    it is not a second orchestration path, just this function no longer
    hiding a choice `build_graph` already made explicit.
    """
    initial_state: OrchestrationState = {
        "message": request.message,
        "workspace_context": request.workspace_context,
        "conversation_id": conversation_id,
        "request_id": request_id,
        "history": history or [],
        "rounds_used": 0,
        "tool_calls_made": [],
        "seen_calls": [],
        "evidence_references": [],
        "limitations": [],
        "last_decision": None,
        "final_answer": None,
    }

    resolved_provider = llm_provider if llm_provider is not None else get_llm_provider()
    graph = build_graph(resolved_provider, client)
    final_state = await graph.ainvoke(initial_state)

    return synthesize_response(final_state)
