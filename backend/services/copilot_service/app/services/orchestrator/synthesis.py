"""
Phase 12 Batch 3 -- final response synthesis. Converts an
`OrchestrationState` (after the graph reaches `synthesize`) into the
frozen `CopilotQueryResponse` (architecture §23). This is the one place
that enforces "never trust the model's evidence IDs blindly" (§12): every
`evidenceId` in the final response is verified against the real,
tool-produced evidence collected during the conversation -- an
unrecognized ID the model claims is silently dropped, never surfaced.
"""

from typing import Dict, List

from backend.services.copilot_service.app.schemas.copilot import CopilotQueryResponse, EvidenceReference, RelatedEntity
from backend.services.copilot_service.app.services.orchestrator.state import OrchestrationState

_VALID_VISUALIZATION_HINTS = {"trend", "distribution", "comparison", "table"}

# Which real evidence source types genuinely support each visualization
# hint -- the model may only request a hint the actual returned evidence
# shape supports (architecture §21 "the hint corresponds to actual
# returned data").
_HINT_REQUIRES_SOURCE_TYPE = {
    "trend": {"trend"},
    "distribution": {"trend", "recommendation"},
    "comparison": {"trend", "business_impact"},
    "table": {"recommendation", "anomaly", "root_cause", "business_impact", "trend", "incident"},
}


def synthesize_response(state: OrchestrationState) -> CopilotQueryResponse:
    final_answer = state["final_answer"]
    real_evidence: List[EvidenceReference] = list(state.get("evidence_references", []))
    real_evidence_by_id: Dict[str, EvidenceReference] = {item.evidence_id: item for item in real_evidence}

    # Only evidence the model actually cited AND that genuinely exists is
    # returned -- an unrecognized claimed ID is dropped silently (never
    # surfaced as if it were real).
    cited_ids = [eid for eid in final_answer.evidence_ids if eid in real_evidence_by_id]
    evidence_references = [real_evidence_by_id[eid] for eid in cited_ids]
    # If the model cited nothing (or nothing valid) but real evidence was
    # gathered, surface all of it rather than silently withholding real,
    # already-retrieved evidence from the response.
    if not evidence_references and real_evidence:
        evidence_references = real_evidence

    related_entities = _derive_related_entities(evidence_references)

    visualization_hint = final_answer.visualization_hint
    if visualization_hint is not None:
        if visualization_hint not in _VALID_VISUALIZATION_HINTS:
            visualization_hint = None
        else:
            supporting_types = _HINT_REQUIRES_SOURCE_TYPE.get(visualization_hint, set())
            present_types = {item.source_type for item in evidence_references}
            if not (supporting_types & present_types):
                visualization_hint = None  # claimed hint has no matching real data -- dropped, not trusted

    # Conflicts (§14.3/§13 of the Batch 3 implementation prompt) are
    # disclosures, never a resolution the orchestrator performs itself --
    # folded into `limitations` since the frozen `CopilotResponse` (§23)
    # has no separate conflicts field; the model may only *disclose* a
    # conflict here, never silently pick a winner (that logic doesn't
    # exist anywhere in this module).
    limitations = list(
        dict.fromkeys(
            [*state.get("limitations", []), *final_answer.limitations, *final_answer.conflicts]
        )
    )  # de-duplicated, order-preserved

    return CopilotQueryResponse(
        answer=final_answer.answer,
        key_findings=list(final_answer.key_findings),
        evidence_references=evidence_references,
        related_entities=related_entities,
        visualization_hint=visualization_hint,
        limitations=limitations,
        conversation_id=state["conversation_id"],
        request_id=state["request_id"],
    )


def _derive_related_entities(evidence_references: List[EvidenceReference]) -> List[RelatedEntity]:
    """Derived only from real evidence source ids -- never from anything the model separately claimed."""
    seen: Dict[str, RelatedEntity] = {}
    for item in evidence_references:
        key = f"{item.source_type}:{item.source_id}"
        if key not in seen:
            seen[key] = RelatedEntity(type=item.source_type, id=item.source_id)
    return list(seen.values())
