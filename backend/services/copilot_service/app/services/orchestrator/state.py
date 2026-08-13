"""
Phase 12 Batch 3 -- orchestration state and LLM decision types.

State fields map directly to the architecture's own LangGraph description
(§20): `Question -> Tool decision -> Tool call -> Evidence -> Optional
next tool (<=3 rounds) -> Answer`. No speculative field is added beyond
what that flow and the response contract (§23) require.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict

from backend.services.copilot_service.app.schemas.copilot import EvidenceReference, WorkspaceContext

MAX_TOOL_ROUNDS = 3  # Phase 12 architecture §19 -- a ceiling, not a target.


@dataclass(frozen=True)
class ToolCallDecision:
    """The LLM (or its stand-in) requests one registered tool call."""

    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalAnswerDecision:
    """
    The LLM (or its stand-in) is ready to answer. `evidence_ids`/
    `conflicts` are the model's own *claims*; the orchestrator (see
    synthesis.py) validates every claimed evidence_id against real
    accumulated evidence before it can appear in the final response --
    an unrecognized ID is dropped, never trusted blindly (§12).
    """

    answer: str
    key_findings: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    related_entity_ids: List[str] = field(default_factory=list)
    visualization_hint: Optional[Literal["trend", "distribution", "comparison", "table"]] = None
    limitations: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)


Decision = ToolCallDecision | FinalAnswerDecision


@dataclass(frozen=True)
class ToolCallRecord:
    """
    One executed (or rejected) tool call, kept for synthesis and
    observability -- never re-executed. `result_evidence_ids` (bounded:
    just the real evidence IDs this call produced, never raw tool
    payload content) is what `prompts.py` actually shows a real provider
    as "tool result data" -- never the raw arguments alone, which would
    tell a real model nothing about what was found.
    """

    tool_name: str
    arguments: Dict[str, Any]
    succeeded: bool
    skipped_reason: Optional[str] = None  # e.g. "unknown_tool", "invalid_arguments", "duplicate_call"
    result_evidence_ids: List[str] = field(default_factory=list)
    result_found: Optional[bool] = None


class OrchestrationState(TypedDict, total=False):
    # Input (Phase 12 architecture §4.1/§25) -- never mutated after the graph starts.
    message: str
    workspace_context: Optional[WorkspaceContext]
    conversation_id: str
    request_id: str

    # Working state.
    rounds_used: int
    tool_calls_made: List[ToolCallRecord]
    seen_calls: List[str]  # canonical "tool_name:sorted_args_json" already executed -- loop prevention
    evidence_references: List[EvidenceReference]
    limitations: List[str]
    last_decision: Optional[Decision]

    # Output.
    final_answer: Optional[FinalAnswerDecision]
