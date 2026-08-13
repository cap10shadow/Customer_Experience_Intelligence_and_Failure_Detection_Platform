from typing import Any, Dict, List

import httpx

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.core.downstream import ToolError, get_json
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.schemas.tools import (
    RecommendationDetail,
    RecommendationStatistics,
    RecommendationToolInput,
    RecommendationToolResult,
)
from backend.services.copilot_service.app.services.tool_registry import ToolDefinition, register_tool

TOOL_NAME = "recommendation"

_BASE_URL = settings.RECOMMENDATION_SERVICE_URL


def _to_detail(payload: Dict[str, Any]) -> RecommendationDetail:
    return RecommendationDetail(
        recommendation_id=str(payload["recommendation_id"]),
        incident_id=str(payload["incident_id"]),
        generation_id=str(payload["generation_id"]),
        category=str(payload["category"]),
        priority=str(payload["priority"]),
        score=payload["score"],
        action=payload["action"],
        created_at=str(payload["created_at"]),
        recommendation_rationale=payload.get("recommendation_rationale"),
        priority_rationale=payload.get("priority_rationale"),
    )


def _evidence_for(detail: RecommendationDetail) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=f"recommendation:{detail.recommendation_id}",
        source_type="recommendation",
        source_id=detail.recommendation_id,
        authority="recommendation_service",
        timestamp=detail.created_at,
    )


async def run(client: httpx.AsyncClient, tool_input: RecommendationToolInput) -> RecommendationToolResult:
    """
    Endpoints (Phase 12 architecture §13.1, verified against
    recommendation_service/app/presentation/api/recommendations.py):
      - GET /recommendations/{recommendation_id}          (single, when recommendation_id given)
      - GET /incidents/{incident_id}/recommendations/latest (when incident_id given)
      - GET /recommendations?limit=                        (otherwise, bounded)
      - GET /recommendations/statistics                    (when include_statistics=True; Step 7.X G-03, approved for Copilot)

    Note: the frozen architecture states no created_at/updated_at field
    exists on these DTOs -- verified against the repository, this is
    incorrect: `created_at` genuinely exists on both
    RecommendationSummaryResponse and RecommendationDetailResponse (see
    recommendation_service/app/presentation/api/schemas.py). Included
    here as real, honest data rather than withheld to match the
    architecture's documented (and here corrected) assumption -- see the
    Batch 2 implementation report.
    """
    try:
        if tool_input.recommendation_id is not None:
            payload = await get_json(client, f"{_BASE_URL}/api/v1/recommendations/{tool_input.recommendation_id}")
            if payload is None:
                return RecommendationToolResult(found=False)
            detail = _to_detail(payload)
            return RecommendationToolResult(
                found=True, recommendations=[detail], evidence_references=[_evidence_for(detail)]
            )

        if tool_input.incident_id is not None:
            payloads = await get_json(
                client,
                f"{_BASE_URL}/api/v1/incidents/{tool_input.incident_id}/recommendations/latest",
                params={"limit": tool_input.limit},
            )
            details = [_to_detail(item) for item in (payloads or [])]
            return RecommendationToolResult(
                found=bool(details), recommendations=details, evidence_references=[_evidence_for(d) for d in details]
            )

        statistics = None
        if tool_input.include_statistics:
            stats_payload = await get_json(client, f"{_BASE_URL}/api/v1/recommendations/statistics")
            statistics = RecommendationStatistics(**stats_payload)

        payloads = await get_json(client, f"{_BASE_URL}/api/v1/recommendations", params={"limit": tool_input.limit})
        details: List[RecommendationDetail] = [_to_detail(item) for item in (payloads or [])]
        return RecommendationToolResult(
            found=bool(details) or statistics is not None,
            recommendations=details,
            statistics=statistics,
            evidence_references=[_evidence_for(d) for d in details],
        )
    except ToolError as exc:
        return RecommendationToolResult(found=False, error=exc.message)


register_tool(
    ToolDefinition(
        name=TOOL_NAME,
        description="Answer questions about a specific recommendation, a bounded list of recommendations, or aggregate recommendation statistics.",
        input_model=RecommendationToolInput,
        output_model=RecommendationToolResult,
        executor=run,
    )
)
