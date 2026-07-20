from backend.shared.constants.enums.base import BaseStringEnum


class IncidentStatus(BaseStringEnum):
    """
    Represents the lifecycle state of an Incident.

    Only OPEN and RESOLVED are driven by the Correlation Engine in Phase 5
    Step 3. INVESTIGATING and MITIGATED are reserved for future phases
    (Root Cause Analysis / Recommendation workflows) and are never assigned
    by any logic in this phase.
    """
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
