import httpx
from fastapi import APIRouter, Depends, Response, status

from backend.services.gateway_service.app.core.auth_dependency import get_current_user
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.dependencies.http_client import get_http_client
from backend.services.gateway_service.app.schemas.copilot import CopilotQueryRequest, CopilotResponse
from backend.services.gateway_service.app.services.copilot_aggregator import delete_conversation, send_copilot_message

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


@router.delete("/copilot/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_copilot_conversation(
    conversation_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
    principal: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """
    Phase 13 Batch 6 (AD-4, §17/§18): deletes one Copilot conversation,
    owner-only, no admin override -- this router's own `require_role("operator")`
    dependency (`main.py`) already gates every route here, matching the
    permission matrix's `operator (owner-only)` entry; ownership itself
    is verified by copilot_service, not here (see
    `copilot_aggregator.delete_conversation`'s docstring). No business
    logic lives here, exactly like `post_copilot_message` above.
    """
    await delete_conversation(client, conversation_id, principal=principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
