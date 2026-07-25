from backend.services.evaluation_service.app.application.evaluation_statistics import EvaluationStatistics
from backend.services.evaluation_service.app.domain.evaluation_repository import EvaluationRepository

# Internal page size used only for walking the repository to compute
# statistics -- independent of, and not bounded by, the public API's
# pagination `limit`/`max limit` (see presentation/api/evaluations.py).
_SCAN_PAGE_SIZE = 200


class EvaluationStatisticsService:
    """
    Evaluation Statistics Service

    Ownership:
    Owned by the Evaluation Service's application layer.

    Operational Purpose:
    Computes aggregate statistics (counts by rating, average scores) across
    all persisted Evaluations. Explicitly NOT a repository responsibility
    (per the approved architecture) -- this service depends only on
    `EvaluationRepository`'s existing read operations (`list_by_incident`),
    never on a dedicated statistics query method, and performs its own
    aggregation in the Application layer.

    Architectural Boundaries:
    - Depends only on the Domain-defined `EvaluationRepository` interface,
      the same Dependency Inversion `EvaluationOrchestrator` follows.
    - Contains no scoring or business rules -- it aggregates values already
      computed by QualityEngine/ExplainabilityEngine/ConfidenceAnalyzer and
      persisted verbatim; it never re-evaluates anything.
    - Walks the repository's paginated `list_by_incident(incident_id=None, ...)`
      in fixed-size pages until exhausted. This is a simple, correct MVP
      approach appropriate to the current data volume; if the Evaluation
      table grows large enough to make full-table aggregation in the
      Application layer impractical, a dedicated read-optimized query would
      be a future, separately-justified change -- not introduced here.
    """

    def __init__(self, repository: EvaluationRepository) -> None:
        self._repository = repository

    async def compute(self) -> EvaluationStatistics:
        total_count = 0
        quality_rating_counts: dict = {}
        explainability_rating_counts: dict = {}
        quality_score_total = 0
        explainability_score_total = 0
        confidence_total = 0.0

        offset = 0
        while True:
            page = await self._repository.list_by_incident(None, limit=_SCAN_PAGE_SIZE, offset=offset)
            if not page:
                break

            for record in page:
                evaluation = record.evaluation
                total_count += 1

                quality_rating = evaluation.quality_assessment.quality_rating.value
                quality_rating_counts[quality_rating] = quality_rating_counts.get(quality_rating, 0) + 1

                explainability_rating = evaluation.explainability_assessment.explainability_rating.value
                explainability_rating_counts[explainability_rating] = (
                    explainability_rating_counts.get(explainability_rating, 0) + 1
                )

                quality_score_total += evaluation.quality_assessment.quality_score
                explainability_score_total += evaluation.explainability_assessment.explainability_score
                confidence_total += evaluation.confidence_summary.average_confidence

            offset += _SCAN_PAGE_SIZE

        if total_count == 0:
            return EvaluationStatistics(total_count=0)

        return EvaluationStatistics(
            total_count=total_count,
            quality_rating_counts=quality_rating_counts,
            explainability_rating_counts=explainability_rating_counts,
            average_quality_score=quality_score_total / total_count,
            average_explainability_score=explainability_score_total / total_count,
            average_confidence=confidence_total / total_count,
        )
