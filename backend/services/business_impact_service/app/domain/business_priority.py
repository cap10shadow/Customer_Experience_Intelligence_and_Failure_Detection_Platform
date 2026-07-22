from backend.shared.constants.enums.base import BaseStringEnum


class BusinessPriority(BaseStringEnum):
    """
    Represents the deterministic business priority derived from an
    Incident's overall impact severity -- how urgently the business should
    act on it, distinct from the technical ImpactLevel it is derived from.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
