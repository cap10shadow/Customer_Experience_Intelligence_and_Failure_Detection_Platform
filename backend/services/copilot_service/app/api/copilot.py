import httpx
from fastapi import APIRouter, Depends, Request

from backend.services.copilot_service.app.dependencies.http_client import get_http_client
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse
from backend.services.copilot_service.app.services.copilot_query_service import handle_query
from backend.shared.observability.correlation import get_request_id

router = APIRouter(tags=["copilot"])


@router.post("/copilot/messages", response_model=CopilotQueryResponse)
async def post_message(
    request: CopilotQueryRequest,
    http_request: Request,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> CopilotQueryResponse:
    """
    Internal-only endpoint, reachable only from gateway_service, never
    the public internet. No business/orchestration logic lives here --
    see copilot_query_service.handle_query's docstring (Phase 12 Batch 3).
    """
    return await handle_query(request, client=client, request_id=get_request_id(http_request))
