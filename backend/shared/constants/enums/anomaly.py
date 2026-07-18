from backend.shared.constants.enums.base import BaseStringEnum

class AnomalyType(BaseStringEnum):
    """Represents operational anomaly classifications supporting temporal reasoning."""
    COMPLAINT_SPIKE = "complaint_spike"
    REGIONAL_SPIKE = "regional_spike"
    CATEGORY_SPIKE = "category_spike"
    SENTIMENT_SHIFT = "sentiment_shift"
    ESCALATION_SURGE = "escalation_surge"
    OPERATIONAL_DEGRADATION = "operational_degradation"
    CHURN_RISK_SURGE = "churn_risk_surge"
    ABNORMAL_PATTERN = "abnormal_pattern"


class AnomalySeverity(BaseStringEnum):
    """Represents operational anomaly severity."""
    INFORMATIONAL = "informational"
    WARNING = "warning"
    SEVERE = "severe"
    CRITICAL = "critical"
