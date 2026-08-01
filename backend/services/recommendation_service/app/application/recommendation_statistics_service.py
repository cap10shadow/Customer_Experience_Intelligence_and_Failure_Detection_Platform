from backend.services.recommendation_service.app.application.recommendation_statistics import RecommendationStatistics
from backend.services.recommendation_service.app.domain.recommendation_repository import RecommendationRepository

# Internal page size used only for walking the repository to compute
# statistics -- independent of, and not bounded by, the public API's
# pagination `limit`/`max limit` (see presentation/api/recommendations.py).
_SCAN_PAGE_SIZE = 200


class RecommendationStatisticsService:
    """
    Recommendation Statistics Service

    Ownership:
    Owned by the Recommendation Service's application layer.

    Operational Purpose:
    Computes aggregate statistics (counts by category, counts by priority,
    average score) across all persisted Recommendations. Explicitly NOT a
    repository responsibility -- this service depends only on
    `RecommendationRepository`'s existing read operations
    (`list_by_incident`), never on a dedicated statistics query method, and
    performs its own aggregation in the Application layer. The same
    pattern already established by `evaluation_service`'s
    `EvaluationStatisticsService`.

    Architectural Boundaries:
    - Depends only on the Domain-defined `RecommendationRepository`
      interface -- the same Dependency Inversion every other Application
      component in this service follows.
    - Contains no scoring or business rules -- it aggregates values already
      computed by the (frozen) Step 1 Rules/Consolidator and persisted
      verbatim; it never re-evaluates anything.
    - Walks the repository's paginated `list_by_incident(incident_id=None, ...)`
      in fixed-size pages until exhausted -- a simple, correct MVP approach
      appropriate to current data volume, matching the same documented
      tradeoff `EvaluationStatisticsService` already accepted.
    """

    def __init__(self, repository: RecommendationRepository) -> None:
        self._repository = repository

    async def compute(self) -> RecommendationStatistics:
        total_count = 0
        category_counts: dict = {}
        priority_counts: dict = {}
        score_total = 0

        offset = 0
        while True:
            page = await self._repository.list_by_incident(None, limit=_SCAN_PAGE_SIZE, offset=offset)
            if not page:
                break

            for record in page:
                recommendation = record.recommendation
                total_count += 1

                category = recommendation.category.value
                category_counts[category] = category_counts.get(category, 0) + 1

                priority = recommendation.priority.value
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

                score_total += recommendation.score

            offset += _SCAN_PAGE_SIZE

        if total_count == 0:
            return RecommendationStatistics(total_count=0)

        return RecommendationStatistics(
            total_count=total_count,
            category_counts=category_counts,
            priority_counts=priority_counts,
            average_score=score_total / total_count,
        )
