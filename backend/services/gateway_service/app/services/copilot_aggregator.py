from typing import Any, Dict

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import delete_resource, post_resource
from backend.services.gateway_service.app.core.errors import AuthenticationError, AuthorizationError, DownstreamServiceError, ResourceNotFoundError
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.schemas.copilot import (
    CopilotQueryRequest,
    CopilotResponse,
    EvidenceReference,
    RelatedEntity,
)
from backend.shared.security.internal_auth import PRINCIPAL_USER_ID_HEADER, internal_service_headers


async def send_copilot_message(
    client: httpx.AsyncClient, request: CopilotQueryRequest, *, principal: AuthenticatedUser
) -> CopilotResponse:
    """
    Forwards a Copilot request to copilot_service and maps its
    snake_case response back to the public, camelCase Gateway DTO. Phase
    12 Batch 1: copilot_service has no tool/LLM logic yet, so this call
    always returns an honest placeholder response -- the Gateway performs
    no calculation and adds nothing copilot_service doesn't already
    provide, exactly like every other aggregator in this module.

    Phase 13 Batch 4 (AD-5, §14): carries the shared internal-service
    credential and the Gateway-attested `principal.user_id` (never
    `email`/`roles`).

    Phase 13 Batch 6 (AD-4, §16/§17): copilot_service now persists
    `principal.user_id` as `owner_id` and enforces real ownership on
    every create/continue -- a genuine `401` (no principal) or `403`
    (not this conversation's owner) is a real, distinct outcome that
    must reach the caller as the Gateway's own matching error, never a
    generic `502` (see `post_resource`'s docstring for why this uses it
    instead of `post_json`).
    """
    body: Dict[str, Any] = {"message": request.message, "conversation_id": request.conversationId}
    if request.workspaceContext is not None:
        body["workspace_context"] = {
            "workspace": request.workspaceContext.workspace,
            "incident_id": request.workspaceContext.incidentId,
            "recommendation_id": request.workspaceContext.recommendationId,
            "filters": request.workspaceContext.filters,
            "time_range": request.workspaceContext.timeRange,
        }

    url = f"{settings.COPILOT_SERVICE_URL}/api/v1/copilot/messages"
    response = await post_resource(
        client,
        url,
        json=body,
        extra_headers={**internal_service_headers(), PRINCIPAL_USER_ID_HEADER: str(principal.user_id)},
    )
    if response.status_code == 401:
        raise AuthenticationError("Authentication required.")
    if response.status_code == 403:
        raise AuthorizationError("You do not have access to this conversation.")
    if response.status_code >= 400:
        raise DownstreamServiceError(f"{url} returned status {response.status_code}.")
    return _to_response(response.json())


async def delete_conversation(client: httpx.AsyncClient, conversation_id: str, *, principal: AuthenticatedUser) -> None:
    """
    Deletes one Copilot conversation (Phase 13 Batch 6, AD-4, §17/§18):
    forwards `DELETE /api/v1/copilot/conversations/{id}` to
    copilot_service with the shared internal-service credential and the
    Gateway-attested `principal.user_id` -- copilot_service, not this
    aggregator, is the sole authority on whether `principal` owns this
    conversation (never re-implemented here). `204` maps to a plain
    return; `404`/`403`/`401` are real, distinct outcomes copilot_service
    can legitimately produce and must be surfaced to the caller as the
    Gateway's own matching error, never collapsed into a generic `502`
    the way `get_json`/`post_json`/`patch_json`'s shared ">=400 ->
    DownstreamServiceError" contract would (see `delete_resource`'s
    docstring for why this route uses it instead of `patch_json`).
    """
    response = await delete_resource(
        client,
        f"{settings.COPILOT_SERVICE_URL}/api/v1/copilot/conversations/{conversation_id}",
        extra_headers={**internal_service_headers(), PRINCIPAL_USER_ID_HEADER: str(principal.user_id)},
    )
    if response.status_code == 204:
        return
    if response.status_code == 404:
        raise ResourceNotFoundError(
            f"Conversation {conversation_id} was not found.", details={"conversationId": conversation_id}
        )
    if response.status_code == 403:
        raise AuthorizationError("You do not have permission to delete this conversation.")
    if response.status_code == 401:
        raise AuthenticationError("Authentication required.")
    raise DownstreamServiceError(
        f"{settings.COPILOT_SERVICE_URL}/api/v1/copilot/conversations/{conversation_id} returned status {response.status_code}."
    )


def _to_response(payload: Dict[str, Any]) -> CopilotResponse:
    return CopilotResponse(
        answer=payload["answer"],
        keyFindings=payload.get("key_findings", []),
        evidenceReferences=[
            EvidenceReference(
                evidenceId=item["evidence_id"],
                sourceType=item["source_type"],
                sourceId=item["source_id"],
                authority=item.get("authority"),
                timestamp=item.get("timestamp"),
            )
            for item in payload.get("evidence_references", [])
        ],
        relatedEntities=[
            RelatedEntity(type=item["type"], id=item["id"]) for item in payload.get("related_entities", [])
        ],
        visualizationHint=payload.get("visualization_hint"),
        limitations=payload.get("limitations", []),
        conversationId=payload["conversation_id"],
        requestId=payload["request_id"],
    )
