# Recommendation Precedence Policy -- the shared, deterministic ordering
# used by RecommendationConsolidator, per the frozen architecture:
#
#   Priority -> Recommendation Category Precedence -> Recommendation Score
#   -> Rule Evaluation Order
#
# Implemented as a shared policy inside the Domain, exactly as the frozen
# architecture requires, using the same fixed-ordered-tuple + index-lookup
# style already established by this platform's other deterministic
# classification tables (e.g. Business Impact's SEVERITY_BANDS).

from typing import Tuple

from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority

# Most urgent first. Used only to rank Priority tiers relative to each
# other for ordering -- never to derive a Priority from anything.
PRIORITY_ORDER: Tuple[RecommendationPriority, ...] = (
    RecommendationPriority.CRITICAL,
    RecommendationPriority.HIGH,
    RecommendationPriority.MEDIUM,
    RecommendationPriority.LOW,
)

# Highest precedence first. Reflects operational urgency of the category
# itself, independent of any one Recommendation's Priority or Score --
# e.g. an ESCALATE recommendation outranks a MONITOR recommendation of the
# same Priority and Score simply because escalation is the more consequential
# category of action.
CATEGORY_PRECEDENCE: Tuple[RecommendationCategory, ...] = (
    RecommendationCategory.ESCALATE,
    RecommendationCategory.MITIGATE,
    RecommendationCategory.SLA_PROTECTION,
    RecommendationCategory.INFRASTRUCTURE_ACTION,
    RecommendationCategory.OPERATIONAL_ACTION,
    RecommendationCategory.CUSTOMER_COMMUNICATION,
    RecommendationCategory.INVESTIGATE,
    RecommendationCategory.MONITOR,
)


def priority_rank(priority: RecommendationPriority) -> int:
    """Lower rank = higher urgency = ordered first."""
    return PRIORITY_ORDER.index(priority)


def category_precedence_index(category: RecommendationCategory) -> int:
    """Lower index = higher precedence = ordered first."""
    return CATEGORY_PRECEDENCE.index(category)
