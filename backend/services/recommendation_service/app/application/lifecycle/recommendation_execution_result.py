import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExecutionOutcome(str, Enum):
    """
    The three terminal outcomes of one execution-lifecycle run, per the
    frozen Failure Model. Exactly one of these is always reached -- there
    is no fourth, partial, or pending state once `execute()` returns.
    """

    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class RecommendationExecutionResult:
    """
    The result `RecommendationLifecycleService.execute()` returns to its
    caller (the Event Consumer). `outcome` is always set; `generation_id`
    is set for COMPLETED and for a duplicate REJECTED (the id of the
    RecommendationGeneration the duplicate event already produced);
    `recommendation_count` is set only for COMPLETED; `reason` is a short,
    human-readable explanation set for REJECTED and FAILED.
    """

    outcome: ExecutionOutcome
    generation_id: Optional[uuid.UUID] = None
    recommendation_count: Optional[int] = None
    reason: Optional[str] = None
