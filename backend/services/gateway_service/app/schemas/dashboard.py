from typing import List, Literal, Optional

from pydantic import BaseModel

# Mirrors frontend/src/workspaces/dashboard/types.ts's vocabulary exactly --
# these are the Gateway's public contract, not a re-export of any backend
# domain enum, so they stay in lockstep with the frozen frontend types
# rather than whatever a downstream service's enum happens to be named.
OperationalStateLevel = Literal["stable", "elevated", "critical"]
TrendDirection = Literal["up", "down", "steady"]
ImportanceLevel = Literal["high", "medium", "low"]


class HealthIndicatorDTO(BaseModel):
    id: str
    label: str
    level: OperationalStateLevel
    trend: TrendDirection
    detail: str


class CriticalSituationDTO(BaseModel):
    id: str
    headline: str
    detail: str


class KeyChangeDTO(BaseModel):
    id: str
    headline: str
    direction: TrendDirection
    detail: str


class FocusAreaDTO(BaseModel):
    id: str
    headline: str
    reason: str


class OperationalBriefDTO(BaseModel):
    level: OperationalStateLevel
    summary: str
    healthIndicators: List[HealthIndicatorDTO]
    criticalSituations: List[CriticalSituationDTO]
    keyChanges: List[KeyChangeDTO]
    # No backend capability produces a "focus area" concept -- always
    # empty rather than fabricated (Part 2 scope).
    focusAreas: List[FocusAreaDTO]


class DecisionOpportunityDTO(BaseModel):
    """
    Descriptive only, per the frozen P1-1 rule: built solely from real
    recommendation fields (category, priority, action, score, incident
    association). Never claims a lifecycle/decision state -- no such state
    exists in recommendation_service today.
    """

    id: str
    headline: str
    importance: ImportanceLevel
    reason: str
    nextDecision: str
    drillDownPath: Optional[str] = None
    drillDownLabel: Optional[str] = None


class OperationalStoryDTO(BaseModel):
    id: str
    headline: str
    situation: str
    significance: str
    direction: str
    context: str
    drillDownPath: Optional[str] = None
    drillDownLabel: Optional[str] = None


class AppliedFiltersDTO(BaseModel):
    """
    Echoes back exactly what the Gateway actually applied -- never more.
    region/businessUnit/productScope/userScope are rejected by the route
    (see api/dashboard.py's NO-FAKE-FILTER handling) before this DTO is
    ever built, so they are always None here today; the fields exist so a
    future capability that does support one of them has somewhere to
    report a real value without a response-shape change.
    """

    timeRange: str
    region: Optional[str] = None
    businessUnit: Optional[str] = None
    productScope: Optional[str] = None
    userScope: Optional[str] = None


class DashboardResponse(BaseModel):
    operationalBrief: OperationalBriefDTO
    decisionSummary: List[DecisionOpportunityDTO]
    investigationEntryPoints: List[OperationalStoryDTO]
    appliedFilters: AppliedFiltersDTO
    # Human-readable notes about any non-essential downstream source that
    # was unavailable when this response was built (Batch 3 SS21 / Batch 4C
    # SS15's endpoint-specific partial-failure rule) -- e.g. "Recommendation
    # data is temporarily unavailable." Empty when everything succeeded.
    # Supporting Evidence is deliberately absent from this DTO entirely
    # (Batch 2 SS2: no backend capability exists for it in Step 7).
    warnings: List[str] = []
