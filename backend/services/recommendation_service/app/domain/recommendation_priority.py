from backend.shared.constants.enums.base import BaseStringEnum


class RecommendationPriority(BaseStringEnum):
    """
    Represents the categorical urgency of one Recommendation, communicating
    how soon the organization should act -- deliberately distinct from
    `Recommendation.score`, which exists only for ranking, analytics, and
    dashboards. A Recommendation's priority and score are set independently
    by the rule that produced it, never derived from one another.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
