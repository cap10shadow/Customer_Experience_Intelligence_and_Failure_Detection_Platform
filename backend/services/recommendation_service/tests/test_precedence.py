from backend.services.recommendation_service.app.domain.precedence import (
    CATEGORY_PRECEDENCE,
    PRIORITY_ORDER,
    category_precedence_index,
    priority_rank,
)
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority


def test_priority_order_covers_every_priority():
    assert set(PRIORITY_ORDER) == set(RecommendationPriority)


def test_category_precedence_covers_every_category():
    assert set(CATEGORY_PRECEDENCE) == set(RecommendationCategory)


def test_priority_rank_orders_critical_first():
    assert priority_rank(RecommendationPriority.CRITICAL) < priority_rank(RecommendationPriority.HIGH)
    assert priority_rank(RecommendationPriority.HIGH) < priority_rank(RecommendationPriority.MEDIUM)
    assert priority_rank(RecommendationPriority.MEDIUM) < priority_rank(RecommendationPriority.LOW)


def test_category_precedence_orders_escalate_first_and_monitor_last():
    assert category_precedence_index(RecommendationCategory.ESCALATE) == 0
    assert category_precedence_index(RecommendationCategory.MONITOR) == len(CATEGORY_PRECEDENCE) - 1


def test_category_precedence_is_a_total_order_with_no_duplicates():
    indices = [category_precedence_index(category) for category in RecommendationCategory]
    assert sorted(indices) == list(range(len(RecommendationCategory)))


def test_is_deterministic():
    assert priority_rank(RecommendationPriority.HIGH) == priority_rank(RecommendationPriority.HIGH)
    assert category_precedence_index(RecommendationCategory.MITIGATE) == category_precedence_index(
        RecommendationCategory.MITIGATE
    )
