import httpx
from fastapi import APIRouter, Depends

from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.copilot import CopilotQueryRequest, CopilotResponse
from backend.services.gateway_service.app.services.copilot_aggregator import send_copilot_message

router = APIRouter(tags=["copilot"])


@router.post("/copilot/messages", response_model=CopilotResponse)
async def post_copilot_message(
    request: CopilotQueryRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
) -> CopilotResponse:
    """
    Phase 12 Batch 1: forwards to copilot_service, which has no tool/LLM
    logic yet and always returns an honest placeholder response. No
    business logic lives here -- see copilot_aggregator.send_copilot_message.
    """
    return await send_copilot_message(client, request)
