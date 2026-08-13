import httpx

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.orchestrator.orchestrator_service import run_orchestration


async def handle_query(
    request: CopilotQueryRequest, *, client: httpx.AsyncClient, request_id: str
) -> CopilotQueryResponse:
    """
    Phase 12 Batch 3: delegates to the bounded LangGraph orchestration
    turn (orchestrator/orchestrator_service.py) instead of Batch 1's
    fixed placeholder response. With no LLM provider configured
    (`NullLLMProvider`, the default in this environment -- verified: no
    LLM credentials exist anywhere in this repository), the orchestrator
    itself produces the honest "no language model configured" answer;
    this function no longer needs its own placeholder text.
    """
    return await run_orchestration(request, client=client, request_id=request_id)
