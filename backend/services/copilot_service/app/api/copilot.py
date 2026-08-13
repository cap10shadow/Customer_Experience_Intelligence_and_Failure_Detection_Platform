from fastapi import APIRouter, Request

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.copilot_query_service import handle_query
from backend.shared.observability.correlation import get_request_id

router = APIRouter(tags=["copilot"])


@router.post("/copilot/messages", response_model=CopilotQueryResponse)
async def post_message(request: CopilotQueryRequest, http_request: Request) -> CopilotQueryResponse:
    """
    Internal-only endpoint (Phase 12 Batch 1) -- reachable only from
    gateway_service, never the public internet. No business/tool logic
    lives here; see copilot_query_service.handle_query's docstring.
    """
    return await handle_query(request, request_id=get_request_id(http_request))
