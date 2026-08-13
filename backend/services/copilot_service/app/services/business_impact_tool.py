from typing import Any, Dict

import httpx

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.core.downstream import ToolError, get_json
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.schemas.tools import (
    BusinessImpactDetail,
    BusinessImpactToolInput,
    BusinessImpactToolResult,
)
from backend.services.copilot_service.app.services.tool_registry import ToolDefinition, register_tool

TOOL_NAME = "business_impact"

_BASE_URL = settings.BUSINESS_IMPACT_SERVICE_URL


def _to_detail(payload: Dict[str, Any]) -> BusinessImpactDetail:
    return BusinessImpactDetail(
        assessment_id=str(payload["assessment_id"]),
        incident_id=str(payload["incident_id"]),
        root_cause_id=str(payload["root_cause_id"]),
        financial=str(payload["financial"]),
        customer=str(payload["customer"]),
        operational=str(payload["operational"]),
        sla=str(payload["sla"]),
        reputation=str(payload["reputation"]),
        overall_score=payload["overall_score"],
        overall_severity=str(payload["overall_severity"]),
        business_priority=str(payload["business_priority"]),
        confidence=payload["confidence"],
        estimated_affected_customers=payload["estimated_affected_customers"],
        explanation=payload.get("explanation", ""),
        status=str(payload["status"]),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
    )


def _evidence_for(detail: BusinessImpactDetail) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=f"business_impact:{detail.assessment_id}",
        source_type="business_impact",
        source_id=detail.assessment_id,
        authority="business_impact_service",
        timestamp=detail.updated_at,
    )


async def run(client: httpx.AsyncClient, tool_input: BusinessImpactToolInput) -> BusinessImpactToolResult:
    """
    Endpoints (Phase 12 architecture §13.4, verified against
    business_impact_service/app/api/business_impact.py):
      - GET /business-impact?incident_id=   (preferred, when incident_id given -- most recent assessment)
      - GET /business-impact/{assessment_id} (when assessment_id given)

    This service has no mutation endpoint at all (verified) -- no
    forbidden-endpoint note is needed.
    """
    if tool_input.incident_id is None and tool_input.assessment_id is None:
        return BusinessImpactToolResult(found=False, error="Either incident_id or assessment_id is required.")

    try:
        if tool_input.incident_id is not None:
            assessments = await get_json(
                client, f"{_BASE_URL}/api/v1/business-impact", params={"incident_id": tool_input.incident_id}
            )
            payload = assessments[0] if assessments else None
        else:
            payload = await get_json(client, f"{_BASE_URL}/api/v1/business-impact/{tool_input.assessment_id}")
    except ToolError as exc:
        return BusinessImpactToolResult(found=False, error=exc.message)

    if payload is None:
        return BusinessImpactToolResult(found=False)

    detail = _to_detail(payload)
    return BusinessImpactToolResult(found=True, assessment=detail, evidence_references=[_evidence_for(detail)])


register_tool(
    ToolDefinition(
        name=TOOL_NAME,
        description="Report the business impact assessment (financial/customer/operational/SLA/reputation) of an incident.",
        input_model=BusinessImpactToolInput,
        output_model=BusinessImpactToolResult,
        executor=run,
    )
)
