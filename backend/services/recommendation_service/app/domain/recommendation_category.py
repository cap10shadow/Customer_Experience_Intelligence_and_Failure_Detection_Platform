from backend.shared.constants.enums.base import BaseStringEnum


class RecommendationCategory(BaseStringEnum):
    """
    Represents the deterministic classification of one operational
    recommendation. Modeled as a Domain Enum, per the frozen architecture,
    specifically to prevent free-text categories -- every Recommendation
    Rule must classify its output into exactly one of these.
    """

    MONITOR = "monitor"
    INVESTIGATE = "investigate"
    MITIGATE = "mitigate"
    ESCALATE = "escalate"
    CUSTOMER_COMMUNICATION = "customer_communication"
    INFRASTRUCTURE_ACTION = "infrastructure_action"
    OPERATIONAL_ACTION = "operational_action"
    SLA_PROTECTION = "sla_protection"
