import httpx

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.core.downstream import ToolError, get_json
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.schemas.tools import (
    RecommendationDecisionStatusInput,
    RecommendationDecisionStatusResult,
)
from backend.services.copilot_service.app.services.tool_registry import ToolDefinition, register_tool

TOOL_NAME = "recommendation_decision_status"

_BASE_URL = settings.RECOMMENDATION_SERVICE_URL


async def run(
    client: httpx.AsyncClient, tool_input: RecommendationDecisionStatusInput
) -> RecommendationDecisionStatusResult:
    """
    Phase 12 architecture §11/§13.2 (F2, resolved): strictly read-only.
    Reads `decision`/`decision_note`/`decided_at` from the existing
    `GET /recommendations/{recommendation_id}` response only -- this
    module contains no reference to, and cannot reach,
    `PATCH /recommendations/{id}/decision` (core/downstream.py exposes
    no PATCH helper at all). A `decision` of `None` means "no decision
    recorded yet" -- a legitimate state, never fabricated as a value.
    """
    try:
        payload = await get_json(
            client, f"{_BASE_URL}/api/v1/recommendations/{tool_input.recommendation_id}"
        )
    except ToolError as exc:
        return RecommendationDecisionStatusResult(found=False, error=exc.message)

    if payload is None:
        return RecommendationDecisionStatusResult(found=False)

    recommendation_id = str(payload["recommendation_id"])
    decided_at = payload.get("decided_at")
    evidence_references = []
    if decided_at is not None:
        evidence_references.append(
            EvidenceReference(
                evidence_id=f"recommendation_decision:{recommendation_id}",
                source_type="recommendation",
                source_id=recommendation_id,
                authority="recommendation_service",
                timestamp=str(decided_at),
            )
        )

    return RecommendationDecisionStatusResult(
        found=True,
        recommendation_id=recommendation_id,
        decision=payload.get("decision"),
        decision_note=payload.get("decision_note"),
        decided_at=str(decided_at) if decided_at is not None else None,
        evidence_references=evidence_references,
    )


register_tool(
    ToolDefinition(
        name=TOOL_NAME,
        description="Report the current persisted decision state (approved/rejected/deferred/pending) of one recommendation. Read-only -- never writes a decision.",
        input_model=RecommendationDecisionStatusInput,
        output_model=RecommendationDecisionStatusResult,
        executor=run,
    )
)
