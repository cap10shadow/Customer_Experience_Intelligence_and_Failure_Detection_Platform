from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict

# Phase 12 Batch 1 -- internal (snake_case) Copilot contract. Mirrors the
# frozen architecture's §23 CopilotResponse shape exactly
# (docs/architecture/phase-12/PHASE_12_ARCHITECTURE.md) -- no field added,
# none omitted. `gateway_service/app/schemas/copilot.py` is the public,
# camelCase counterpart; `copilot_aggregator.py` is the only place that
# translates between the two.

WorkspaceName = Literal["dashboard", "investigations", "recommendations", "analytics", "administration"]


class WorkspaceContext(BaseModel):
    """
    Exactly the five fields §4.1 of the frozen architecture permits as
    Copilot launch context -- input only, never authority over workspace
    state. No additional field is accepted (`extra="forbid"` below).
    """

    model_config = ConfigDict(extra="forbid")

    workspace: WorkspaceName
    incident_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    filters: Optional[Dict[str, str]] = None
    time_range: Optional[str] = None


class CopilotQueryRequest(BaseModel):
    """Internal request body for `POST /api/v1/copilot/messages`."""

    model_config = ConfigDict(extra="forbid")

    message: str
    conversation_id: Optional[str] = None
    workspace_context: Optional[WorkspaceContext] = None


class EvidenceReference(BaseModel):
    """§14.1 evidence shape -- unused (empty list) until Batch 2 populates it with real tool results."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source_type: str
    source_id: str
    authority: Optional[str] = None
    timestamp: Optional[str] = None


class RelatedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    id: str


class CopilotQueryResponse(BaseModel):
    """
    Internal response body -- exactly the frozen §23 `CopilotResponse`
    field set. Batch 1 populates only honest, non-fabricated placeholder
    values (see `copilot_query_service.py`); no tool/LLM logic exists yet.
    """

    model_config = ConfigDict(extra="forbid")

    answer: str
    key_findings: List[str] = []
    evidence_references: List[EvidenceReference] = []
    related_entities: List[RelatedEntity] = []
    visualization_hint: Optional[Literal["trend", "distribution", "comparison", "table"]] = None
    limitations: List[str] = []
    conversation_id: str
    request_id: str
