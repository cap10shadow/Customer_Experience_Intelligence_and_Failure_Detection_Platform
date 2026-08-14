from typing import Dict, List, Optional

import httpx

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.orchestrator.graph import build_graph
from backend.services.copilot_service.app.services.orchestrator.llm_provider import get_llm_provider
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

    llm_provider = get_llm_provider()
    graph = build_graph(llm_provider, client)
    final_state = await graph.ainvoke(initial_state)

    return synthesize_response(final_state)
