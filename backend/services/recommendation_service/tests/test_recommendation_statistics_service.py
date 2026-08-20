import uuid

import pytest

from backend.services.recommendation_service.app.application.recommendation_statistics_service import (
    RecommendationStatisticsService,
    _SCAN_PAGE_SIZE,
)
from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.tests.fakes import FakeRecommendationRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


DATASET_ID = uuid.uuid4()
DATASET_VERSION_ID = uuid.uuid4()


@pytest.mark.anyio
async def test_empty_dataset_returns_zeroed_statistics():
    repository = FakeRecommendationRepository()

    statistics = await RecommendationStatisticsService(repository).compute()

    assert statistics.total_count == 0
    assert statistics.category_counts == {}
    assert statistics.priority_counts == {}
    assert statistics.average_score == 0.0


@pytest.mark.anyio
async def test_populated_dataset_aggregates_correctly(make_recommendation):
    repository = FakeRecommendationRepository()
    await repository.save_many(
        [
            make_recommendation(category=RecommendationCategory.ESCALATE, priority=RecommendationPriority.CRITICAL, score=90),
            make_recommendation(category=RecommendationCategory.ESCALATE, priority=RecommendationPriority.HIGH, score=70),
            make_recommendation(category=RecommendationCategory.MONITOR, priority=RecommendationPriority.LOW, score=30),
        ],
        dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID,
        incident_id="INC-STATS",
        generation_id=uuid.uuid4(),
    )

    statistics = await RecommendationStatisticsService(repository).compute()

    assert statistics.total_count == 3
    assert statistics.category_counts == {"escalate": 2, "monitor": 1}
    assert statistics.priority_counts == {"critical": 1, "high": 1, "low": 1}
    assert statistics.average_score == pytest.approx((90 + 70 + 30) / 3)


@pytest.mark.anyio
async def test_is_deterministic(make_recommendation):
    repository = FakeRecommendationRepository()
    await repository.save_many(
        [make_recommendation(score=50), make_recommendation(score=60)], dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-DET", generation_id=uuid.uuid4()
    )
    service = RecommendationStatisticsService(repository)

    first = await service.compute()
    second = await service.compute()

    assert first == second


@pytest.mark.anyio
async def test_compute_spans_multiple_internal_pages_without_skipping_or_double_counting(make_recommendation):
    """
    Seeds more recommendations than one internal page (_SCAN_PAGE_SIZE),
    forcing compute()'s pagination loop across at least two data-bearing
    pages plus the terminating empty page -- the same regression this
    exact scenario caught for EvaluationStatisticsService.
    """
    repository = FakeRecommendationRepository()
    record_count = _SCAN_PAGE_SIZE + 5
    recommendations = [make_recommendation(incident_id=f"INC-{i:05d}") for i in range(record_count)]
    await repository.save_many(recommendations, dataset_id=DATASET_ID, dataset_version_id=DATASET_VERSION_ID, incident_id="INC-PAGED", generation_id=uuid.uuid4())

    statistics = await RecommendationStatisticsService(repository).compute()

    assert statistics.total_count == record_count
    assert statistics.category_counts == {recommendations[0].category.value: record_count}
    assert statistics.average_score == pytest.approx(recommendations[0].score)
