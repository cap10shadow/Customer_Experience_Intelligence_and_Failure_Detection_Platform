"""
Result types for the evaluation harness. Kept separate from both the
dataset (data) and `checks.py`/`runner.py` (evaluator logic), per the
Batch 6 implementation prompt §5's separation-of-concerns requirement.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Dimension(str, Enum):
    """
    Exactly the nine measures architecture §26 names -- no dimension is
    added or removed. Order matches the architecture's own listing.
    """

    TOOL_SELECTION = "tool_selection"
    ANSWER_GROUNDING = "answer_grounding"
    CITATION_CORRECTNESS = "citation_correctness"
    HALLUCINATION = "hallucination"
    CONFLICT_HANDLING = "conflict_handling"
    UNSUPPORTED_REQUEST_HANDLING = "unsupported_request_handling"
    SCOPE_PRESERVATION = "scope_preservation"
    SAFETY_READ_ONLY = "safety_read_only"
    COMPLETENESS = "completeness"


class CheckStatus(str, Enum):
    """
    The general pass/fail vocabulary used uniformly across all nine
    dimensions for aggregate scoring. The Batch 6 implementation prompt
    §8 additionally asks the specifically-named no-fabrication
    (`HALLUCINATION`) dimension to distinguish SUPPORTED / UNSUPPORTED /
    NOT APPLICABLE -- `checks.py`'s hallucination check surfaces that
    exact vocabulary in its own `detail` text, so both requirements are
    satisfied without maintaining two parallel status enums for what is,
    underneath, still a pass/fail/not-applicable outcome. `NOT_APPLICABLE`
    is used honestly whenever the check depends on real backing data or a
    real LLM provider this environment does not have -- never silently
    scored as PASS.
    """

    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class DimensionResult:
    dimension: Dimension
    status: CheckStatus
    detail: str

    def to_dict(self) -> Dict[str, str]:
        return {"dimension": self.dimension.value, "status": self.status.value, "detail": self.detail}


@dataclass
class CaseResult:
    case_id: str
    category: str
    provider_used: str
    dimension_results: List[DimensionResult] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        """A case passes only if no dimension actually failed -- NOT_APPLICABLE and a case-level error (e.g. malformed case) never count as a pass."""
        if self.error is not None:
            return False
        return all(result.status != CheckStatus.FAIL for result in self.dimension_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "provider_used": self.provider_used,
            "passed": self.passed,
            "error": self.error,
            "dimensions": [result.to_dict() for result in self.dimension_results],
        }


@dataclass
class EvaluationReport:
    """
    The aggregate result of one evaluation run. Bounded, non-sensitive
    content only (§11 of the Batch 6 implementation prompt): case ids,
    categories, dimension statuses/short detail strings, and which
    provider actually executed. Never a raw prompt, provider API key, or
    database credential -- none of those are ever collected in the first
    place (see `runner.py`).
    """

    cases: List[CaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def passed_count(self) -> int:
        return sum(1 for case in self.cases if case.passed)

    @property
    def failed_count(self) -> int:
        return self.total - self.passed_count

    def dimension_summary(self) -> Dict[str, Dict[str, int]]:
        """Per-dimension pass/fail/not_applicable counts across every case that exercised it."""
        summary: Dict[str, Dict[str, int]] = {}
        for case in self.cases:
            for result in case.dimension_results:
                bucket = summary.setdefault(result.dimension.value, {"pass": 0, "fail": 0, "not_applicable": 0})
                bucket[result.status.value] += 1
        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "dimension_summary": self.dimension_summary(),
            "cases": [case.to_dict() for case in self.cases],
        }
