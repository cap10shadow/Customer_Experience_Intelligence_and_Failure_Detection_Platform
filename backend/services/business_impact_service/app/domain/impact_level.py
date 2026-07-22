from backend.shared.constants.enums.base import BaseStringEnum


class ImpactLevel(BaseStringEnum):
    """
    Represents deterministic business-impact magnitude for a single
    dimension, keyed to the same magnitude-based, deterministic scoring
    philosophy as anomaly severity (Phase 5 Step 2) and root-cause
    confidence (Phase 6 Step 1). NONE means the dimension shows no
    meaningful impact signal.
    """
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
