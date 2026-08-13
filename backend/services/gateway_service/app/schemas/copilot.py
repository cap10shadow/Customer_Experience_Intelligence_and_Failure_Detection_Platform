from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

# Phase 12 Batch 1 -- public (camelCase) Copilot contract, matching the
# frozen architecture's §23 CopilotResponse shape exactly
# (docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md). Mirrors every
# other Gateway schema's convention (see schemas/recommendations.py): the
# Gateway performs no calculation and adds nothing copilot_service
# doesn't already provide -- copilot_aggregator.py only translates casing.

WorkspaceName = Literal["dashboard", "investigations", "recommendations", "analytics", "administration"]


class WorkspaceContext(BaseModel):
    workspace: WorkspaceName
    incidentId: Optional[str] = None
    recommendationId: Optional[str] = None
    filters: Optional[Dict[str, str]] = None
    timeRange: Optional[str] = None


class CopilotQueryRequest(BaseModel):
    """Public request body for `POST /api/v1/copilot/messages`."""

    message: str
    conversationId: Optional[str] = None
    workspaceContext: Optional[WorkspaceContext] = None


class EvidenceReference(BaseModel):
    evidenceId: str
    sourceType: str
    sourceId: str
    authority: Optional[str] = None
    timestamp: Optional[str] = None


class RelatedEntity(BaseModel):
    type: str
    id: str


class CopilotResponse(BaseModel):
    """Public response body -- exactly the frozen §23 `CopilotResponse` field set."""

    answer: str
    keyFindings: List[str] = []
    evidenceReferences: List[EvidenceReference] = []
    relatedEntities: List[RelatedEntity] = []
    visualizationHint: Optional[Literal["trend", "distribution", "comparison", "table"]] = None
    limitations: List[str] = []
    conversationId: str
    requestId: str
