from backend.shared.constants.enums.base import BaseStringEnum

class RecommendationType(BaseStringEnum):
    """Represents actionable recommendation categories."""
    OPERATIONAL_FIX = "operational_fix"
    ESCALATION = "escalation"
    CUSTOMER_INTERVENTION = "customer_intervention"
    PROCESS_OPTIMIZATION = "process_optimization"
    STAFFING_ADJUSTMENT = "staffing_adjustment"
    INVENTORY_ADJUSTMENT = "inventory_adjustment"
    WORKFLOW_REVIEW = "workflow_review"
    MONITORING_INCREASE = "monitoring_increase"


class RecommendationStatus(BaseStringEnum):
    """Represents operational execution state of recommendations."""
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class RecommendationPriority(BaseStringEnum):
    """Represents operational importance of a recommendation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
