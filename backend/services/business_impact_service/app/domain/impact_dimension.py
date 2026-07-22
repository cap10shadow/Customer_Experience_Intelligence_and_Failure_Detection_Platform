from backend.shared.constants.enums.base import BaseStringEnum


class ImpactDimension(BaseStringEnum):
    """Represents one axis of business impact evaluated by a single ImpactRule."""
    FINANCIAL = "financial"
    CUSTOMER = "customer"
    OPERATIONAL = "operational"
    SLA = "sla"
    REPUTATION = "reputation"
