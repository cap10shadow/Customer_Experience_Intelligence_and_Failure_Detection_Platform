from backend.shared.constants.enums.base import BaseStringEnum

class AnomalyType(BaseStringEnum):
    """Represents operational anomaly classifications supporting temporal reasoning."""
    COMPLAINT_SPIKE = "complaint_spike"
    REGIONAL_SPIKE = "regional_spike"
    CATEGORY_SPIKE = "category_spike"
    URGENCY_SPIKE = "urgency_spike"
    SENTIMENT_SHIFT = "sentiment_shift"
    ESCALATION_SURGE = "escalation_surge"
    OPERATIONAL_DEGRADATION = "operational_degradation"
    CHURN_RISK_SURGE = "churn_risk_surge"
    ABNORMAL_PATTERN = "abnormal_pattern"


class AnomalySeverity(BaseStringEnum):
    """
    Represents deterministic anomaly severity, keyed to the magnitude of
    percentage change between a current and baseline time window.
    NORMAL means no anomaly: the change fell within expected bounds.
    """
    NORMAL = "normal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyStatus(BaseStringEnum):
    """Represents the lifecycle state of an anomaly in `active_anomalies`."""
    ACTIVE = "active"
    RESOLVED = "resolved"


class AnomalyEventType(BaseStringEnum):
    """Represents the kind of lifecycle event recorded in `anomaly_history`."""
    DETECTED = "detected"
    UPDATED = "updated"
    RESOLVED = "resolved"
