from backend.shared.constants.enums.base import BaseStringEnum


class BusinessImpactAssessmentStatus(BaseStringEnum):
    """
    Represents the lifecycle state of a persisted BusinessImpactAssessment.

    Only ACTIVE is assigned by Phase 7 Step 2 (an assessment is created
    once, from a single deterministic engine run, and is immutable
    thereafter -- there is no update endpoint). Additional lifecycle states
    are reserved for Phase 7 Step 3 and are never assigned by any logic in
    this step.
    """
    ACTIVE = "active"
