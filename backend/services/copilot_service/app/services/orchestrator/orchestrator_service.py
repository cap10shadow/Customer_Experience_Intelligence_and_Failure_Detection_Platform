import uuid

import httpx

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.orchestrator.graph import build_graph
from backend.services.copilot_service.app.services.orchestrator.llm_provider import get_llm_provider
from backend.services.copilot_service.app.services.orchestrator.state import OrchestrationState
from backend.services.copilot_service.app.services.orchestrator.synthesis import synthesize_response
from backend.services.copilot_service.app.services import tools_bootstrap  # noqa: F401 -- import-for-registration, see its own docstring


async def run_orchestration(
    request: CopilotQueryRequest, *, client: httpx.AsyncClient, request_id: str
) -> CopilotQueryResponse:
    """
    Phase 12 Batch 3 -- runs one bounded orchestration turn (Question ->
    Tool decision -> Tool call -> Evidence -> Optional next tool (<=3
    rounds) -> Answer, architecture §20) and returns the frozen
    `CopilotResponse` shape. `conversation_id` minting is unchanged from
    Batch 1: `copilot_service` owns conversation identity (COPILOT-002);
    still purely ephemeral here -- no persistence exists until Batch 4.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())

    initial_state: OrchestrationState = {
        "message": request.message,
        "workspace_context": request.workspace_context,
        "conversation_id": conversation_id,
        "request_id": request_id,
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
