import uuid

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, CopilotQueryResponse

# Phase 12 Batch 1 -- no tool registry, no LLM, no evidence retrieval
# exists yet (Batches 2/3). This is the one honest placeholder answer
# every request gets until that work lands; it must never be mistaken
# for a real finding (no-fabrication rule, Phase 12 architecture §21).
_PLACEHOLDER_ANSWER = "Copilot tool orchestration is not yet implemented."
_PLACEHOLDER_LIMITATION = "Tool orchestration and evidence retrieval are not yet implemented (Phase 12 Batch 1)."


async def handle_query(request: CopilotQueryRequest, *, request_id: str) -> CopilotQueryResponse:
    """
    Builds the Batch 1 placeholder response. `conversation_id` is minted
    here (copilot_service owns conversation identity, per COPILOT-002)
    when the caller doesn't supply one; a supplied value is echoed back
    unchanged. Purely ephemeral in Batch 1 -- nothing is persisted yet.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())

    return CopilotQueryResponse(
        answer=_PLACEHOLDER_ANSWER,
        key_findings=[],
        evidence_references=[],
        related_entities=[],
        visualization_hint=None,
        limitations=[_PLACEHOLDER_LIMITATION],
        conversation_id=conversation_id,
        request_id=request_id,
    )
