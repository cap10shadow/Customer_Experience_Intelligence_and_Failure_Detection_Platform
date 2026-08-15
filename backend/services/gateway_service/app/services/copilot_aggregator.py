from typing import Any, Dict

import httpx

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import post_json
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
    `email`/`roles`). copilot_service does not yet persist this as
    `owner_id` -- that remains explicitly a later batch's scope
    (COPILOT-002/AD-4); this batch only makes the header trustworthy
    and available.
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

    response = await post_json(
        client,
        f"{settings.COPILOT_SERVICE_URL}/api/v1/copilot/messages",
        json=body,
        extra_headers={**internal_service_headers(), PRINCIPAL_USER_ID_HEADER: str(principal.user_id)},
    )
    return _to_response(response)


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
