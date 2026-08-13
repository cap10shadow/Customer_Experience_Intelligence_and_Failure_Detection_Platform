from typing import Any, Dict

import httpx

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.core.downstream import ToolError, get_json
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.schemas.tools import (
    RootCauseDetail,
    RootCauseEvidenceItem,
    RootCauseToolInput,
    RootCauseToolResult,
)
from backend.services.copilot_service.app.services.tool_registry import ToolDefinition, register_tool

TOOL_NAME = "root_cause"

_BASE_URL = settings.ROOT_CAUSE_SERVICE_URL


def _to_detail(payload: Dict[str, Any]) -> RootCauseDetail:
    return RootCauseDetail(
        root_cause_id=str(payload["id"]),
        incident_id=str(payload["incident_id"]),
        cause=str(payload["cause"]),
        confidence_score=payload["confidence_score"],
        confidence_level=payload["confidence_level"],
        explanation=payload.get("explanation", ""),
        rule_version=payload["rule_version"],
        status=str(payload["status"]),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        evidence=[
            RootCauseEvidenceItem(type=str(item["type"]), description=item["description"], weight=item["weight"])
            for item in payload.get("evidence", [])
        ],
    )


def _evidence_for(detail: RootCauseDetail) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=f"root_cause:{detail.root_cause_id}",
        source_type="root_cause",
        source_id=detail.root_cause_id,
        authority="root_cause_service",
        timestamp=detail.updated_at,
    )


async def run(client: httpx.AsyncClient, tool_input: RootCauseToolInput) -> RootCauseToolResult:
    """
    Endpoints (Phase 12 architecture §13.3, verified against
    root_cause_service/app/api/root_causes.py):
      - GET /incidents/{incident_id}/root-cause  (preferred, when incident_id given)
      - GET /root-causes/{root_cause_id}          (when root_cause_id given)

    Forbidden and unreferenced anywhere in this module: PATCH .../confirm,
    PATCH .../reject, POST .../refresh (§19).
    """
    if tool_input.incident_id is None and tool_input.root_cause_id is None:
        return RootCauseToolResult(found=False, error="Either incident_id or root_cause_id is required.")

    try:
        if tool_input.incident_id is not None:
            payload = await get_json(
                client, f"{_BASE_URL}/api/v1/incidents/{tool_input.incident_id}/root-cause"
            )
        else:
            payload = await get_json(client, f"{_BASE_URL}/api/v1/root-causes/{tool_input.root_cause_id}")
    except ToolError as exc:
        return RootCauseToolResult(found=False, error=exc.message)

    if payload is None:
        return RootCauseToolResult(found=False)

    detail = _to_detail(payload)
    return RootCauseToolResult(found=True, root_cause=detail, evidence_references=[_evidence_for(detail)])


register_tool(
    ToolDefinition(
        name=TOOL_NAME,
        description="Explain the identified root cause of an incident, including its supporting evidence and confidence.",
        input_model=RootCauseToolInput,
        output_model=RootCauseToolResult,
        executor=run,
    )
)
