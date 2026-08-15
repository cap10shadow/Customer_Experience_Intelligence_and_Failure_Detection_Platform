import httpx
from fastapi import APIRouter, Depends

from backend.services.gateway_service.app.core.auth_dependency import get_current_user
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.copilot import CopilotQueryRequest, CopilotResponse
from backend.services.gateway_service.app.services.copilot_aggregator import send_copilot_message

router = APIRouter(tags=["copilot"])


@router.post("/copilot/messages", response_model=CopilotResponse)
async def post_copilot_message(
    request: CopilotQueryRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    principal: AuthenticatedUser = Depends(get_current_user),
) -> CopilotResponse:
    """
    Phase 12 Batch 1: forwards to copilot_service, which has no tool/LLM
    logic yet and always returns an honest placeholder response. No
    business logic lives here -- see copilot_aggregator.send_copilot_message.

    Phase 13 Batch 4 (AD-5): `principal` is the same resolved
    `AuthenticatedUser` this router's `require_role("operator")`
    dependency (main.py) already validated -- cached per-request by
    FastAPI, not re-decoded here; forwarded to copilot_service via
    `send_copilot_message`.
    """
    return await send_copilot_message(client, request, principal=principal)
