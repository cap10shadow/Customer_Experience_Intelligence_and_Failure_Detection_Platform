import asyncio
from typing import Any, Dict, List, Optional

import httpx

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.core.downstream import ToolError, get_json
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.schemas.tools import (
    InvestigationAnomaly,
    InvestigationIncident,
    InvestigationNlpSummary,
    InvestigationToolInput,
    InvestigationToolResult,
)
from backend.services.copilot_service.app.services.business_impact_tool import _to_detail as _business_impact_detail
from backend.services.copilot_service.app.services.recommendation_tool import _to_detail as _recommendation_detail
from backend.services.copilot_service.app.services.root_cause_tool import _to_detail as _root_cause_detail
from backend.services.copilot_service.app.services.tool_registry import ToolDefinition, register_tool

TOOL_NAME = "investigation"

# Phase 12 architecture §8: there is no investigation_service. This tool
# is a Copilot-owned, read-only composition calling the same five real
# domain services investigation_aggregator.py (gateway_service) composes
# -- an independent code path, never via the public Gateway (§6/§20).


async def run(client: httpx.AsyncClient, tool_input: InvestigationToolInput) -> InvestigationToolResult:
    incident_id = tool_input.incident_id
    limitations: List[str] = []
    evidence_references: List[EvidenceReference] = []

    try:
        incident_payload = await get_json(
            client, f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents/{incident_id}"
        )
    except ToolError as exc:
        return InvestigationToolResult(found=False, error=exc.message)

    if incident_payload is None:
        return InvestigationToolResult(found=False)

    incident = InvestigationIncident(
        incident_id=str(incident_payload["id"]),
        incident_key=incident_payload["incident_key"],
        title=incident_payload["title"],
        severity=str(incident_payload["severity"]),
        status=str(incident_payload["status"]),
        confidence_score=incident_payload["confidence_score"],
        summary=incident_payload.get("summary", ""),
        started_at=str(incident_payload["started_at"]),
        last_updated_at=str(incident_payload["last_updated_at"]),
        resolved_at=str(incident_payload["resolved_at"]) if incident_payload.get("resolved_at") else None,
    )
    evidence_references.append(
        EvidenceReference(
            evidence_id=f"incident:{incident.incident_id}",
            source_type="incident",
            source_id=incident.incident_id,
            authority="anomaly_service",
            timestamp=incident.last_updated_at,
        )
    )

    anomalies_result, root_cause_payload, business_impact_payloads, recommendation_payloads = await asyncio.gather(
        _fetch_degraded(
            get_json(client, f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents/{incident_id}/anomalies"),
            limitations,
            "Anomaly evidence for this incident is temporarily unavailable.",
            default=[],
        ),
        _fetch_legitimate_absence(
            get_json(client, f"{settings.ROOT_CAUSE_SERVICE_URL}/api/v1/incidents/{incident_id}/root-cause"),
            limitations,
            "Root cause data for this incident is temporarily unavailable.",
        ),
        _fetch_degraded(
            get_json(
                client,
                f"{settings.BUSINESS_IMPACT_SERVICE_URL}/api/v1/business-impact",
                params={"incident_id": incident_id},
            ),
            limitations,
            "Business impact data for this incident is temporarily unavailable.",
            default=[],
        ),
        _fetch_degraded(
            get_json(
                client, f"{settings.RECOMMENDATION_SERVICE_URL}/api/v1/incidents/{incident_id}/recommendations/latest"
            ),
            limitations,
            "Recommendation data for this incident is temporarily unavailable.",
            default=[],
        ),
    )

    anomalies = [
        InvestigationAnomaly(
            anomaly_id=str(item["id"]),
            type=str(item["type"]),
            severity=str(item["severity"]),
            entity_type=item["entity_type"],
            entity_value=item.get("entity_value"),
            explanation=item.get("explanation", ""),
            triggered_rule=item.get("triggered_rule", ""),
            first_detected_at=str(item["first_detected_at"]),
            last_seen_at=str(item["last_seen_at"]),
        )
        for item in anomalies_result
    ]
    for anomaly in anomalies:
        evidence_references.append(
            EvidenceReference(
                evidence_id=f"anomaly:{anomaly.anomaly_id}",
                source_type="anomaly",
                source_id=anomaly.anomaly_id,
                authority="anomaly_service",
                timestamp=anomaly.last_seen_at,
            )
        )

    root_cause = None
    if root_cause_payload is not None:
        root_cause = _root_cause_detail(root_cause_payload)
        evidence_references.append(
            EvidenceReference(
                evidence_id=f"root_cause:{root_cause.root_cause_id}",
                source_type="root_cause",
                source_id=root_cause.root_cause_id,
                authority="root_cause_service",
                timestamp=root_cause.updated_at,
            )
        )

    business_impact = None
    if business_impact_payloads:
        business_impact = _business_impact_detail(business_impact_payloads[0])
        evidence_references.append(
            EvidenceReference(
                evidence_id=f"business_impact:{business_impact.assessment_id}",
                source_type="business_impact",
                source_id=business_impact.assessment_id,
                authority="business_impact_service",
                timestamp=business_impact.updated_at,
            )
        )

    latest_recommendations = [_recommendation_detail(item) for item in recommendation_payloads]
    for recommendation in latest_recommendations:
        evidence_references.append(
            EvidenceReference(
                evidence_id=f"recommendation:{recommendation.recommendation_id}",
                source_type="recommendation",
                source_id=recommendation.recommendation_id,
                authority="recommendation_service",
                timestamp=recommendation.created_at,
            )
        )

    nlp_summary = await _fetch_nlp_summary(client, incident_id, anomalies, limitations)
    if nlp_summary is not None:
        evidence_references.append(
            EvidenceReference(
                evidence_id=f"nlp_summary:{incident_id}:{nlp_summary.issue_category}",
                source_type="nlp_enrichment_summary",
                source_id=incident_id,
                authority="nlp_service",
                # nlp_service's enrichment summary carries no computation
                # timestamp (verified) -- never fabricated.
                timestamp=None,
            )
        )

    return InvestigationToolResult(
        found=True,
        incident=incident,
        anomalies=anomalies,
        root_cause=root_cause,
        business_impact=business_impact,
        latest_recommendations=latest_recommendations,
        nlp_summary=nlp_summary,
        limitations=limitations,
        evidence_references=evidence_references,
    )


async def _fetch_degraded(coro, limitations: List[str], message: str, *, default: Any) -> Any:
    """Failure here is non-essential: record an honest gap statement and continue with `default`."""
    try:
        result = await coro
    except ToolError:
        limitations.append(message)
        return default
    return result if result is not None else default


async def _fetch_legitimate_absence(coro, limitations: List[str], message: str) -> Optional[Dict[str, Any]]:
    """A 404 here (`get_json` -> None) is a legitimate absence, not a failure -- no limitation recorded for it."""
    try:
        return await coro
    except ToolError:
        limitations.append(message)
        return None


async def _fetch_nlp_summary(
    client: httpx.AsyncClient, incident_id: str, anomalies: List[InvestigationAnomaly], limitations: List[str]
) -> Optional[InvestigationNlpSummary]:
    """
    Mirrors investigation_aggregator.py's own selection rule exactly (not
    new domain logic -- the same deterministic tie-break already
    established): an incident's category-dimension anomaly scopes a real
    NLP enrichment aggregate to that category and detection window. No
    category-dimension anomaly => a legitimate absence, not a failure.
    """
    category_anomalies = sorted(
        (a for a in anomalies if a.entity_type == "category" and a.entity_value),
        key=lambda a: a.entity_value or "",
    )
    if not category_anomalies:
        return None

    anomaly = category_anomalies[0]
    try:
        payload = await get_json(
            client,
            f"{settings.NLP_SERVICE_URL}/api/v1/enrichments/summary",
            params={
                "issue_category": anomaly.entity_value,
                "start_date": anomaly.first_detected_at,
                "end_date": anomaly.last_seen_at,
            },
        )
    except ToolError:
        limitations.append("NLP enrichment summary is temporarily unavailable.")
        return None

    if payload is None:
        return None
    return InvestigationNlpSummary(
        issue_category=str(payload["issue_category"]),
        total_count=payload["total_count"],
        sentiment_counts=payload.get("sentiment_counts", {}),
    )


register_tool(
    ToolDefinition(
        name=TOOL_NAME,
        description="Assemble a cross-domain view of one incident: anomalies, root cause, business impact, latest recommendation, and NLP context.",
        input_model=InvestigationToolInput,
        output_model=InvestigationToolResult,
        executor=run,
    )
)
