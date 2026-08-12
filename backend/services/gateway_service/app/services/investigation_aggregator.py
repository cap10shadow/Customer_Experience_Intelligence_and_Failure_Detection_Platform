import asyncio
from typing import Any, Optional

import httpx

from backend.services.gateway_service.app.core.aggregation import await_optional
from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.confidence import band_to_confidence_level
from backend.services.gateway_service.app.core.downstream import get_json
from backend.services.gateway_service.app.core.errors import ResourceNotFoundError
from backend.services.gateway_service.app.schemas.investigation import (
    BusinessImpactDimensionSummaryDTO,
    EvidenceItemDTO,
    InvestigationResponse,
    ObservationDTO,
    RecommendedActionDTO,
    RootCauseExplanationDTO,
)

# The five canonical Business Impact dimensions (BI-002/ARB-003) in the
# order BusinessImpactAssessmentResponse exposes them as separate fields.
_IMPACT_DIMENSIONS = ("financial", "customer", "operational", "sla", "reputation")

_DIMENSION_HEADLINE = {
    "none": "No material impact detected",
    "low": "Limited impact detected",
    "medium": "Moderate impact detected",
    "high": "Significant impact detected",
    "critical": "Severe impact detected",
}


async def build_investigation(client: httpx.AsyncClient, incident_id: str) -> InvestigationResponse:
    """
    Aggregates one Investigation from real backend capabilities, keyed
    throughout by `incident_id` -- no separate investigation identity is
    introduced (Batch 3 SS2).

    Essential (failure fails the whole request):
      - the Incident itself (anomaly_service) -- a 404 here means the
        Incident genuinely doesn't exist and is propagated as a real
        Gateway 404, not a generic downstream failure.
      - Root Cause, when root_cause_service itself is unreachable/erroring
        (NOT when it legitimately has no RootCause yet -- see below).
        Batch 1 SS14's own worked example groups "root cause" with "core
        incident, findings" as required, distinct from Business Impact,
        which that same example explicitly names as the one allowed to be
        "unavailable" in a degraded response.

    Legitimate absence, not a failure (no warning, no error):
      - Root Cause 404 ("not yet analyzed" -- root_cause_service's own
        domain design: created via a separate call, may not exist yet).
      - Business Impact empty/404 ("not yet assessed").
      - Recommendation empty/404 ("no recommendation generated yet").

    Non-essential (degrades with a warning, does not fail the request):
      - Anomalies-for-incident (feeds Evidence only).
      - Business Impact, when business_impact_service itself is
        unreachable/erroring (as opposed to legitimately empty).
      - Latest Recommendation, when recommendation_service itself is
        unreachable/erroring.
    """
    warnings: list[str] = []

    incident = await _fetch_incident(client, incident_id)

    anomalies_task = asyncio.create_task(_fetch_anomalies(client, incident_id))
    business_impact_task = asyncio.create_task(_fetch_business_impact(client, incident_id))
    recommendation_task = asyncio.create_task(_fetch_latest_recommendation(client, incident_id))

    # Root Cause is essential-if-erroring, legitimate-if-absent -- handled
    # explicitly rather than through await_optional, since a 404 here must
    # NOT be treated the same as a warning-worthy degradation.
    root_cause = await get_json(client, f"{settings.ROOT_CAUSE_SERVICE_URL}/api/v1/incidents/{incident_id}/root-cause")

    anomalies = await await_optional(
        anomalies_task, warnings, f"Anomaly evidence for incident {incident_id} is temporarily unavailable.", default=[]
    )
    business_impact_list = await await_optional(
        business_impact_task,
        warnings,
        f"Business impact for incident {incident_id} is temporarily unavailable.",
        default=[],
    )
    recommendations = await await_optional(
        recommendation_task,
        warnings,
        f"Recommendation data for incident {incident_id} is temporarily unavailable.",
        default=[],
    )

    return InvestigationResponse(
        incidentId=str(incident_id),
        observation=_build_observation(incident),
        evidence=_build_evidence(incident, anomalies),
        rootCause=_build_root_cause(root_cause),
        businessImpact=_build_business_impact(business_impact_list[0] if business_impact_list else None),
        # ARB-008 (Confidence Remains Stage-Specific): business_impact_service
        # exposes only a raw `confidence: int` with no stage-specific band
        # classification of its own. The Gateway must not invent one --
        # least of all by reusing root_cause_service's confidence bands,
        # which are Root-Cause-domain semantics, not a portable platform
        # scale (see docs/DECISIONS.md ARB-008; confirmed anomaly_service's
        # own severity bands use entirely different thresholds against a
        # different measurement, proving the bands are not interchangeable
        # across stages). Always None until Business Impact provides its
        # own classification -- a Step 7.X capability if ever needed, not
        # a Gateway concern.
        businessImpactConfidenceLevel=None,
        recommendedNextStep=_build_recommended_next_step(recommendations[0] if recommendations else None),
        warnings=warnings,
    )


async def _fetch_incident(client: httpx.AsyncClient, incident_id: str) -> dict[str, Any]:
    incident = await get_json(client, f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents/{incident_id}")
    if incident is None:
        raise ResourceNotFoundError(f"Incident {incident_id} was not found.", details={"incidentId": incident_id})
    return incident


async def _fetch_anomalies(client: httpx.AsyncClient, incident_id: str) -> list[dict[str, Any]]:
    anomalies = await get_json(client, f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents/{incident_id}/anomalies")
    return anomalies or []


async def _fetch_business_impact(client: httpx.AsyncClient, incident_id: str) -> list[dict[str, Any]]:
    assessments = await get_json(
        client, f"{settings.BUSINESS_IMPACT_SERVICE_URL}/api/v1/business-impact", params={"incident_id": incident_id}
    )
    return assessments or []


async def _fetch_latest_recommendation(client: httpx.AsyncClient, incident_id: str) -> list[dict[str, Any]]:
    recommendations = await get_json(
        client, f"{settings.RECOMMENDATION_SERVICE_URL}/api/v1/incidents/{incident_id}/recommendations/latest"
    )
    return recommendations or []


def _build_observation(incident: dict[str, Any]) -> ObservationDTO:
    return ObservationDTO(
        headline=incident.get("title", "Untitled incident"),
        description=incident.get("summary", ""),
    )


def _build_evidence(incident: dict[str, Any], anomalies: list[dict[str, Any]]) -> list[EvidenceItemDTO]:
    """
    Built only from sources with a real, queryable-by-incident API today:
    one item per linked anomaly (Anomaly Detection) plus one correlation
    synthesis item when more than one anomaly was linked (Incident
    Correlation). "NLP Intelligence" evidence is intentionally omitted --
    nlp_service exposes enrichments by complaint_id/enrichment_id only,
    with no endpoint to list them by incident_id, so there is no real
    capability to source that evidence type from today.
    """
    items: list[EvidenceItemDTO] = [
        EvidenceItemDTO(
            id=str(anomaly["id"]),
            headline=anomaly.get("explanation", "An anomaly was detected."),
            detail=f"Triggered rule: {anomaly.get('triggered_rule', 'unknown')}.",
            source="Anomaly Detection",
        )
        for anomaly in anomalies
    ]

    if len(anomalies) > 1:
        items.append(
            EvidenceItemDTO(
                id=f"{incident['id']}-correlation",
                headline=f"{len(anomalies)} related anomalies were grouped into this incident",
                detail=incident.get("summary", ""),
                source="Incident Correlation",
            )
        )

    return items


def _build_root_cause(root_cause: Optional[dict[str, Any]]) -> Optional[RootCauseExplanationDTO]:
    if root_cause is None:
        return None

    cause_label = str(root_cause["cause"]).replace("_", " ").title()
    return RootCauseExplanationDTO(
        headline=f"Most likely cause: {cause_label}",
        reasoning=root_cause.get("explanation", ""),
        confidenceLevel=band_to_confidence_level(root_cause["confidence_level"]),
    )


def _build_business_impact(assessment: Optional[dict[str, Any]]) -> list[BusinessImpactDimensionSummaryDTO]:
    if assessment is None:
        return []

    summaries = []
    for dimension in _IMPACT_DIMENSIONS:
        level = str(assessment.get(dimension, "none")).lower()
        summaries.append(
            BusinessImpactDimensionSummaryDTO(
                dimension=dimension,
                headline=_DIMENSION_HEADLINE.get(level, "Impact detected"),
                detail=f"{dimension.title()} impact assessed as {level}.",
            )
        )
    return summaries


def _build_recommended_next_step(recommendation: Optional[dict[str, Any]]) -> Optional[RecommendedActionDTO]:
    if recommendation is None:
        return None

    return RecommendedActionDTO(
        headline=recommendation.get("action") or "Review recommendation",
        reason=(
            f"{str(recommendation.get('category', 'recommendation')).replace('_', ' ').title()} recommendation "
            f"(score {recommendation.get('score')})."
        ),
        recommendationId=str(recommendation["recommendation_id"]),
    )
