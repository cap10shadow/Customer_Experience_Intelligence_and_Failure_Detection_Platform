"""
Evaluation dataset loading and validation (Batch 6 implementation prompt
§5): a versionable, deterministic, human-readable JSON fixture file
(`dataset/cases.json`), kept entirely separate from evaluator logic
(`checks.py`/`runner.py`). Every case here is a synthetic evaluation
fixture -- never a real production observation (see `cases.json`'s own
top-level `"dataset_kind"` field and each case's `description`) -- and a
malformed entry fails loudly, at load time, via Pydantic validation
rather than being silently skipped or crashing the runner mid-execution.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_DATASET_PATH = Path(__file__).parent / "dataset" / "cases.json"


class ScriptedToolCallSpec(BaseModel):
    """Declarative form of `orchestrator.state.ToolCallDecision` -- converted by `providers.py`, never imported directly by the dataset."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["tool_call"]
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ScriptedFinalAnswerSpec(BaseModel):
    """Declarative form of `orchestrator.state.FinalAnswerDecision`."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["final_answer"]
    answer: str
    key_findings: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    visualization_hint: Optional[Literal["trend", "distribution", "comparison", "table"]] = None
    limitations: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)


class CaseExpectations(BaseModel):
    """
    Every field is optional -- a case only exercises the dimensions its
    expectations actually populate (`checks.py` reports `NOT_APPLICABLE`
    for any dimension a case leaves unset, never a silent pass).
    """

    model_config = ConfigDict(extra="forbid")

    expected_tool_names: Optional[List[str]] = None
    forbidden_tool_names: Optional[List[str]] = None
    expect_empty_evidence: Optional[bool] = None
    expect_nonempty_evidence: Optional[bool] = None
    expected_source_types: Optional[List[str]] = None
    expect_refusal: Optional[bool] = None
    expect_conflict_disclosure: Optional[bool] = None
    forbidden_evidence_ids: Optional[List[str]] = None
    expected_incident_id: Optional[str] = None
    expected_recommendation_id: Optional[str] = None


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: str
    description: str
    message: str
    workspace_context: Optional[Dict[str, Any]] = None
    conversation_id_from_case: Optional[str] = None
    scripted_decisions: Optional[List[ScriptedToolCallSpec | ScriptedFinalAnswerSpec]] = None
    expectations: CaseExpectations = Field(default_factory=CaseExpectations)


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_kind: Literal["synthetic_evaluation_fixtures"]
    cases: List[EvaluationCase]


class DatasetValidationError(Exception):
    """Raised for a malformed dataset file -- never silently skipped, never crashes with a raw traceback the caller can't act on."""


def load_dataset(path: Optional[Path] = None) -> EvaluationDataset:
    target = path or _DATASET_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetValidationError(f"Evaluation dataset not found at {target}.") from exc
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(f"Evaluation dataset at {target} is not valid JSON: {exc}") from exc

    try:
        return EvaluationDataset.model_validate(raw)
    except ValidationError as exc:
        raise DatasetValidationError(f"Evaluation dataset at {target} failed validation: {exc}") from exc
