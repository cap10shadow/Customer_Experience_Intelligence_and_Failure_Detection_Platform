from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EvaluationMetadata:
    """
    Lineage and versioning metadata for one Evaluation.

    `evaluation_version` identifies which version of the Evaluation Service's
    deterministic logic produced this record -- the same versioning
    discipline as Root Cause's `rule_version` -- and is assigned here, in the
    domain layer, since it is a property of the engine logic itself, not of
    persistence.

    `previous_evaluation_id` links this Evaluation to the prior Evaluation
    for the same Incident, if one exists. Step 1 has no persistence or
    repository layer, so there is no way to look up a prior record yet --
    it is always None here by design, not a placeholder. Populating it is
    Phase 8 Step 2's responsibility (querying the `evaluations` table for
    the most recent prior record before persisting a new one).
    """
    evaluation_version: str
    previous_evaluation_id: Optional[str] = None
