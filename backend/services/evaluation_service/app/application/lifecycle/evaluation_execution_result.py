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
class EvaluationExecutionResult:
    """
    The result `EvaluationLifecycleService.execute()` returns to its caller
    (the Event Consumer). `outcome` is always set; `evaluation_id` is set
    only for COMPLETED (and, for a duplicate REJECTED, the id of the
    Evaluation the duplicate event already produced); `reason` is a short,
    human-readable explanation set for REJECTED and FAILED.
    """

    outcome: ExecutionOutcome
    evaluation_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
