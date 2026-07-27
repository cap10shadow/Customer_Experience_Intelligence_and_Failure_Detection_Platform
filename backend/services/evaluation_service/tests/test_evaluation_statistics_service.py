"""
Unit tests for EvaluationStatisticsService, focused on the internal
pagination loop in compute() that walks EvaluationRepository.list_by_incident()
in fixed-size pages until exhausted.
"""

import pytest

from backend.services.evaluation_service.app.application.evaluation_statistics_service import (
    _SCAN_PAGE_SIZE,
    EvaluationStatisticsService,
)
from backend.services.evaluation_service.tests.fakes import FakeEvaluationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _seed(repository: FakeEvaluationRepository, make_evaluation, count: int) -> None:
    for i in range(count):
        await repository.save(make_evaluation(incident_id=f"INC-STATS-{i:05d}"))


@pytest.mark.anyio
async def test_compute_spans_multiple_internal_pages_without_skipping_or_double_counting(make_evaluation):
    """
    Seeds more evaluations than one internal page (_SCAN_PAGE_SIZE), forcing
    compute()'s `while True` loop to run across at least two data-bearing
    pages plus the final empty page that terminates it.

    Every seeded evaluation is built from make_evaluation()'s identical
    default inputs, so its quality/explainability/confidence values are
    already known ahead of time. This lets the test assert *exact* expected
    totals and averages that are only correct if every one of `record_count`
    records was counted -- once each, with none skipped and none counted
    twice -- regardless of how many internal pages the loop had to walk.
    """
    repository = FakeEvaluationRepository()
    record_count = _SCAN_PAGE_SIZE + 5  # forces 2 data-bearing pages + 1 terminating empty page
    await _seed(repository, make_evaluation, record_count)

    reference = make_evaluation()
    expected_quality_rating = reference.quality_assessment.quality_rating.value
    expected_explainability_rating = reference.explainability_assessment.explainability_rating.value
    expected_quality_score = reference.quality_assessment.quality_score
    expected_explainability_score = reference.explainability_assessment.explainability_score
    expected_confidence = reference.confidence_summary.average_confidence

    statistics = await EvaluationStatisticsService(repository).compute()

    assert statistics.total_count == record_count
    assert statistics.quality_rating_counts == {expected_quality_rating: record_count}
    assert statistics.explainability_rating_counts == {expected_explainability_rating: record_count}
    assert statistics.average_quality_score == pytest.approx(expected_quality_score)
    assert statistics.average_explainability_score == pytest.approx(expected_explainability_score)
    assert statistics.average_confidence == pytest.approx(expected_confidence)
