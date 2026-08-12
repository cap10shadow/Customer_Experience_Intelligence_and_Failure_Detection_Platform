import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from backend.services.gateway_service.app.core.aggregation import await_optional
from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.downstream import get_json
from backend.services.gateway_service.app.schemas.dashboard import (
    AppliedFiltersDTO,
    CriticalSituationDTO,
    DashboardResponse,
    DecisionOpportunityDTO,
    HealthIndicatorDTO,
    KeyChangeDTO,
    OperationalBriefDTO,
    OperationalStoryDTO,
)

# 'current' and '24h' both resolve to the smallest real granularity the
# backend trend endpoints support (daily buckets) -- there is no capability
# that distinguishes "right now" from "the last 24 hours" more finely.
_TIME_RANGE_TO_DAYS = {"current": 1, "24h": 1, "7d": 7, "30d": 30}

# Bounded on purpose: root cause + business impact enrichment issues one
# extra pair of downstream calls per featured incident, so this stays a
# small, fixed number of calls rather than growing with however many
# incidents happen to be active (the N+1 risk the audit flagged).
_MAX_FEATURED_INCIDENTS = 2
_MAX_DECISION_OPPORTUNITIES = 5

_ACTIVE_STATUSES = {"open", "investigating"}

_SEVERITY_RANK = {"normal": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

# AnomalySeverity (backend-defined enum) -> OperationalStateLevel
# (Dashboard's own three-level scale). A DTO/label transformation, not an
# invented business rule -- the same kind of mapping Batch 2 SS4 sanctions
# for Root Cause confidence (cause/confidence_score/confidence_level ->
# headline/confidence).
_SEVERITY_TO_LEVEL = {
    "critical": "critical",
    "high": "critical",
    "medium": "elevated",
    "low": "stable",
    "normal": "stable",
}

# RecommendationPriority (backend-defined enum) -> ImportanceLevel.
_PRIORITY_TO_IMPORTANCE = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


@dataclass
class DashboardQuery:
    time_range: str


async def build_dashboard(client: httpx.AsyncClient, query: DashboardQuery) -> DashboardResponse:
    """
    Aggregates the Dashboard read model from real backend capabilities.
    Incidents are essential -- Operational Brief, Critical Situations, and
    Investigation Entry Points all derive from them, so a failure fetching
    them fails the whole request (a GatewayError propagates out of this
    function uncaught, per Batch 3 SS21/Batch 4C SS15's endpoint-specific
    partial-failure rule). Trend, recommendation, root-cause, and
    business-impact data are non-essential enrichments: a failure in any
    of them degrades that specific piece of the response and is recorded
    in `warnings`, never fabricated.
    """
    warnings: list[str] = []
    days = _TIME_RANGE_TO_DAYS[query.time_range]

    # Independent downstream calls issued concurrently, not sequentially.
    incidents_task = asyncio.create_task(_fetch_active_incidents(client))
    trend_task = asyncio.create_task(_fetch_volume_trend(client, days))
    recommendations_task = asyncio.create_task(_fetch_recent_recommendations(client))

    incidents = await incidents_task

    volume_trend = await await_optional(
        trend_task, warnings, "Complaint volume trend is temporarily unavailable."
    )
    recommendations = await await_optional(
        recommendations_task, warnings, "Recommendation data is temporarily unavailable.", default=[]
    )

    operational_brief = _build_operational_brief(incidents, volume_trend)
    decision_summary = _build_decision_summary(recommendations)
    investigation_entry_points = await _build_investigation_entry_points(client, incidents, warnings)

    return DashboardResponse(
        operationalBrief=operational_brief,
        decisionSummary=decision_summary,
        investigationEntryPoints=investigation_entry_points,
        appliedFilters=AppliedFiltersDTO(
            timeRange=query.time_range,
            region=None,
            businessUnit=None,
            productScope=None,
            userScope=None,
        ),
        warnings=warnings,
    )


async def _fetch_active_incidents(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    url = f"{settings.ANOMALY_SERVICE_URL}/api/v1/incidents"
    incidents = await get_json(client, url)
    return incidents or []


async def _fetch_volume_trend(client: httpx.AsyncClient, days: int) -> Optional[dict[str, Any]]:
    url = f"{settings.ANOMALY_SERVICE_URL}/api/v1/trends/daily"
    return await get_json(client, url, params={"days": days})


async def _fetch_recent_recommendations(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    url = f"{settings.RECOMMENDATION_SERVICE_URL}/api/v1/recommendations"
    recommendations = await get_json(client, url, params={"limit": _MAX_DECISION_OPPORTUNITIES})
    return recommendations or []


def _max_severity(severities: list[str]) -> str:
    if not severities:
        return "normal"
    return max(severities, key=lambda severity: _SEVERITY_RANK.get(severity, 0))


def _direction(previous: float, latest: float) -> str:
    if latest > previous:
        return "up"
    if latest < previous:
        return "down"
    return "steady"


def _build_operational_brief(
    incidents: list[dict[str, Any]], volume_trend: Optional[dict[str, Any]]
) -> OperationalBriefDTO:
    active_incidents = [incident for incident in incidents if incident.get("status") in _ACTIVE_STATUSES]
    severities = [incident.get("severity", "normal") for incident in active_incidents]
    overall_level = _SEVERITY_TO_LEVEL.get(_max_severity(severities), "stable")

    if not active_incidents:
        summary = "No active incidents detected."
    else:
        summary = f"{len(active_incidents)} active incident(s); highest severity is {_max_severity(severities)}."

    health_indicators: list[HealthIndicatorDTO] = []
    key_changes: list[KeyChangeDTO] = []

    points = (volume_trend or {}).get("complaint_volume", [])
    if len(points) >= 2:
        latest, previous = points[-1], points[-2]
        direction = _direction(previous["count"], latest["count"])
        detail = f"{latest['count']} complaints on {latest['date']}, compared to {previous['count']} the prior day."
        health_indicators.append(
            HealthIndicatorDTO(
                id="complaint-volume",
                label="Complaint volume",
                level=overall_level,
                trend=direction,
                detail=detail,
            )
        )
        key_changes.append(
            KeyChangeDTO(id="complaint-volume-change", headline="Complaint volume", direction=direction, detail=detail)
        )

    critical_situations = [
        CriticalSituationDTO(
            id=str(incident["id"]),
            headline=incident.get("title", "Untitled incident"),
            detail=incident.get("summary", ""),
        )
        for incident in active_incidents
        if incident.get("severity") in ("high", "critical")
    ]

    return OperationalBriefDTO(
        level=overall_level,
        summary=summary,
        healthIndicators=health_indicators,
        criticalSituations=critical_situations,
        keyChanges=key_changes,
        focusAreas=[],
    )


def _build_decision_summary(recommendations: list[dict[str, Any]]) -> list[DecisionOpportunityDTO]:
    opportunities = []
    for recommendation in recommendations:
        priority = recommendation.get("priority", "low")
        category = str(recommendation.get("category", "recommendation")).replace("_", " ").title()
        opportunities.append(
            DecisionOpportunityDTO(
                id=str(recommendation["recommendation_id"]),
                headline=recommendation.get("action") or "Review recommendation",
                importance=_PRIORITY_TO_IMPORTANCE.get(priority, "low"),
                reason=(
                    f"{category} recommendation for incident {recommendation.get('incident_id')} "
                    f"(score {recommendation.get('score')})."
                ),
                nextDecision="Review this recommendation for the associated incident.",
                # The canonical dynamic Recommendation route, wired in Part 4.
                drillDownPath=f"/recommendations/{recommendation['recommendation_id']}",
                drillDownLabel="Review recommendation",
            )
        )
    return opportunities


async def _build_investigation_entry_points(
    client: httpx.AsyncClient, incidents: list[dict[str, Any]], warnings: list[str]
) -> list[OperationalStoryDTO]:
    active_incidents = [incident for incident in incidents if incident.get("status") in _ACTIVE_STATUSES]
    featured = sorted(
        active_incidents,
        key=lambda incident: (_SEVERITY_RANK.get(incident.get("severity"), 0), incident.get("started_at", "")),
        reverse=True,
    )[:_MAX_FEATURED_INCIDENTS]

    stories = await asyncio.gather(*(_build_story(client, incident, warnings) for incident in featured))
    return list(stories)


async def _build_story(
    client: httpx.AsyncClient, incident: dict[str, Any], warnings: list[str]
) -> OperationalStoryDTO:
    incident_id = incident["id"]

    root_cause_task = asyncio.create_task(
        get_json(client, f"{settings.ROOT_CAUSE_SERVICE_URL}/api/v1/incidents/{incident_id}/root-cause")
    )
    business_impact_task = asyncio.create_task(
        get_json(
            client,
            f"{settings.BUSINESS_IMPACT_SERVICE_URL}/api/v1/business-impact",
            params={"incident_id": incident_id},
        )
    )

    root_cause = await await_optional(
        root_cause_task, warnings, f"Root cause for incident {incident_id} is temporarily unavailable."
    )
    business_impact_list = await await_optional(
        business_impact_task,
        warnings,
        f"Business impact for incident {incident_id} is temporarily unavailable.",
        default=[],
    )
    business_impact = business_impact_list[0] if business_impact_list else None

    if root_cause:
        cause_label = str(root_cause["cause"]).replace("_", " ").title()
        direction = f"Most likely cause: {cause_label} (confidence: {root_cause['confidence_level']})."
    else:
        direction = "Root cause analysis has not yet been completed for this incident."

    if business_impact:
        context = (
            f"Business impact: {business_impact['overall_severity']} severity, "
            f"{business_impact['business_priority']} priority."
        )
    else:
        context = "Business impact assessment has not yet been completed for this incident."

    return OperationalStoryDTO(
        id=str(incident_id),
        headline=incident.get("title", "Untitled incident"),
        situation=incident.get("summary", ""),
        significance=(
            f"Severity: {incident.get('severity', 'unknown')}; confidence: {incident.get('confidence_score', 'unknown')}%."
        ),
        direction=direction,
        context=context,
        drillDownPath=f"/investigations/{incident_id}",
        drillDownLabel="Investigate this story",
    )
