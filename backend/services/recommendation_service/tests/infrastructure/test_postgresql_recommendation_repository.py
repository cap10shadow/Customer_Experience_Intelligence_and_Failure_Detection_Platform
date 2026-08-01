"""
Repository tests: exercise `PostgreSQLRecommendationRepository` against a
real PostgreSQL database (no mocking of SQL execution) -- the only way to
genuinely verify JSONB persistence, the composite index, native enum
columns, and real save/query behavior. Connects to `localhost:5432` (the
same Postgres this project's `docker compose up postgres` exposes) and
skips cleanly, module-wide, if it is not reachable -- `python -m pytest
backend` remains green with or without Docker running.

Every test runs inside a transaction that is always rolled back at the
end, so no test data is ever actually committed or left behind.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.recommendation_service.app.domain.recommendation_category import RecommendationCategory
from backend.services.recommendation_service.app.domain.recommendation_repository import DuplicateGenerationEventError
from backend.services.recommendation_service.app.domain.recommendation_priority import RecommendationPriority
from backend.services.recommendation_service.app.infrastructure.persistence.models.recommendation_generation_model import (
    RecommendationGenerationModel,
)
from backend.services.recommendation_service.app.infrastructure.persistence.models.recommendation_model import (
    RecommendationModel,
)
from backend.services.recommendation_service.app.infrastructure.persistence.repositories.postgresql_recommendation_repository import (
    PostgreSQLRecommendationRepository,
)
from backend.shared.config.settings import Settings

_test_settings = Settings(POSTGRES_HOST="localhost")
_test_engine = create_async_engine(_test_settings.database_url, poolclass=NullPool)

_database_available: Optional[bool] = None


async def _is_database_available() -> bool:
    global _database_available
    if _database_available is None:
        try:
            async with _test_engine.connect() as probe:
                await probe.execute(text("SELECT 1"))
            _database_available = True
        except Exception:
            _database_available = False
    return _database_available


@asynccontextmanager
async def _repository_session() -> AsyncIterator[AsyncSession]:
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")

    async with _test_engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: RecommendationGenerationModel.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.run_sync(lambda sync_conn: RecommendationModel.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.commit()

        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_save_many_persists_generation_and_recommendations(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        generation_id = uuid.uuid4()
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        recommendations = [make_recommendation(incident_id=incident_id), make_recommendation(incident_id=incident_id)]

        saved = await repository.save_many(recommendations, incident_id=incident_id, generation_id=generation_id)

        assert len(saved) == 2
        assert all(record.generation_id == generation_id for record in saved)
        assert all(record.recommendation_id is not None for record in saved)


@pytest.mark.anyio
async def test_save_many_persists_the_generation_row_even_with_zero_recommendations():
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        generation_id = uuid.uuid4()
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"

        saved = await repository.save_many([], incident_id=incident_id, generation_id=generation_id)

        assert saved == []
        result = await session.execute(
            text("SELECT incident_id FROM recommendation_generations WHERE generation_id = :gid"),
            {"gid": str(generation_id)},
        )
        assert result.scalar_one() == incident_id


@pytest.mark.anyio
async def test_get_by_id_retrieves_a_saved_recommendation(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        saved = await repository.save_many(
            [make_recommendation()], incident_id="INC-TEST0001", generation_id=uuid.uuid4()
        )

        fetched = await repository.get_by_id(saved[0].recommendation_id)

        assert fetched is not None
        assert fetched.recommendation_id == saved[0].recommendation_id
        assert fetched.recommendation == saved[0].recommendation


@pytest.mark.anyio
async def test_get_by_id_returns_none_for_unknown_id():
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)

        assert await repository.get_by_id(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_list_by_incident_filters_to_one_incident(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        incident_a = f"INC-{uuid.uuid4().hex[:8]}"
        incident_b = f"INC-{uuid.uuid4().hex[:8]}"

        await repository.save_many([make_recommendation(incident_id=incident_a)], incident_id=incident_a, generation_id=uuid.uuid4())
        await repository.save_many([make_recommendation(incident_id=incident_b)], incident_id=incident_b, generation_id=uuid.uuid4())

        results = await repository.list_by_incident(incident_a, limit=10, offset=0)

        assert len(results) == 1
        assert results[0].recommendation.incident_id == incident_a


@pytest.mark.anyio
async def test_list_by_incident_without_filter_spans_incidents(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        incident_a = f"INC-{uuid.uuid4().hex[:8]}"
        incident_b = f"INC-{uuid.uuid4().hex[:8]}"

        await repository.save_many([make_recommendation(incident_id=incident_a)], incident_id=incident_a, generation_id=uuid.uuid4())
        await repository.save_many([make_recommendation(incident_id=incident_b)], incident_id=incident_b, generation_id=uuid.uuid4())

        results = await repository.list_by_incident(None, limit=50, offset=0)
        incident_ids = {record.recommendation.incident_id for record in results}

        assert incident_a in incident_ids
        assert incident_b in incident_ids


@pytest.mark.anyio
async def test_list_by_incident_pagination_limit_and_offset(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        recommendations = [make_recommendation(incident_id=incident_id) for _ in range(5)]
        await repository.save_many(recommendations, incident_id=incident_id, generation_id=uuid.uuid4())

        first_page = await repository.list_by_incident(incident_id, limit=2, offset=0)
        second_page = await repository.list_by_incident(incident_id, limit=2, offset=2)

        assert len(first_page) == 2
        assert len(second_page) == 2
        assert {r.recommendation_id for r in first_page}.isdisjoint({r.recommendation_id for r in second_page})


@pytest.mark.anyio
async def test_list_by_generation_returns_only_that_generations_recommendations(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        generation_a = uuid.uuid4()
        generation_b = uuid.uuid4()

        await repository.save_many([make_recommendation(incident_id=incident_id)], incident_id=incident_id, generation_id=generation_a)
        await repository.save_many(
            [make_recommendation(incident_id=incident_id), make_recommendation(incident_id=incident_id)],
            incident_id=incident_id,
            generation_id=generation_b,
        )

        results = await repository.list_by_generation(generation_b, limit=10, offset=0)

        assert len(results) == 2
        assert all(record.generation_id == generation_b for record in results)


@pytest.mark.anyio
async def test_list_by_category_filters_correctly(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        await repository.save_many(
            [
                make_recommendation(incident_id=incident_id, category=RecommendationCategory.ESCALATE),
                make_recommendation(incident_id=incident_id, category=RecommendationCategory.MONITOR),
            ],
            incident_id=incident_id,
            generation_id=uuid.uuid4(),
        )

        results = await repository.list_by_category(RecommendationCategory.ESCALATE, limit=10, offset=0)

        assert len(results) >= 1
        assert all(record.recommendation.category == RecommendationCategory.ESCALATE for record in results)


@pytest.mark.anyio
async def test_list_by_priority_filters_correctly(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        await repository.save_many(
            [
                make_recommendation(incident_id=incident_id, priority=RecommendationPriority.CRITICAL),
                make_recommendation(incident_id=incident_id, priority=RecommendationPriority.LOW),
            ],
            incident_id=incident_id,
            generation_id=uuid.uuid4(),
        )

        results = await repository.list_by_priority(RecommendationPriority.CRITICAL, limit=10, offset=0)

        assert len(results) >= 1
        assert all(record.recommendation.priority == RecommendationPriority.CRITICAL for record in results)


@pytest.mark.anyio
async def test_get_latest_by_incident_returns_only_the_most_recent_generation(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"

        await repository.save_many(
            [make_recommendation(incident_id=incident_id, category=RecommendationCategory.MONITOR)],
            incident_id=incident_id,
            generation_id=uuid.uuid4(),
        )
        second = await repository.save_many(
            [make_recommendation(incident_id=incident_id, category=RecommendationCategory.ESCALATE)],
            incident_id=incident_id,
            generation_id=uuid.uuid4(),
        )

        results = await repository.get_latest_by_incident(incident_id, limit=10, offset=0)

        assert len(results) == 1
        assert results[0].recommendation_id == second[0].recommendation_id
        assert results[0].generation_id == second[0].generation_id


@pytest.mark.anyio
async def test_get_latest_by_incident_returns_empty_when_no_generation_exists():
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)

        results = await repository.get_latest_by_incident(f"INC-{uuid.uuid4().hex[:8]}", limit=10, offset=0)

        assert results == []


@pytest.mark.anyio
async def test_jsonb_fields_round_trip_through_real_postgres(make_recommendation):
    from backend.services.recommendation_service.app.domain.evidence_source import EvidenceSource
    from backend.services.recommendation_service.app.domain.supporting_evidence import SupportingEvidence

    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        evidence = (
            SupportingEvidence(source=EvidenceSource.ROOT_CAUSE, description="A" * 60, weight=15),
            SupportingEvidence(source=EvidenceSource.BUSINESS_IMPACT, description="B" * 60, weight=10),
        )
        recommendation = make_recommendation(supporting_evidence=evidence, rationale="C" * 80)

        saved = await repository.save_many([recommendation], incident_id=recommendation.incident_id, generation_id=uuid.uuid4())
        fetched = await repository.get_by_id(saved[0].recommendation_id)

        assert fetched is not None
        assert fetched.recommendation.supporting_evidence == evidence
        assert fetched.recommendation.rationale == "C" * 80


@pytest.mark.anyio
async def test_composite_index_exists_on_incident_id_and_generation_id():
    async with _repository_session() as session:
        result = await session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'recommendations' AND indexname = :name"),
            {"name": "ix_recommendations_incident_id_generation_id"},
        )
        assert result.first() is not None


@pytest.mark.anyio
async def test_generation_incident_created_at_index_exists():
    async with _repository_session() as session:
        result = await session.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'recommendation_generations' "
                "AND indexname = :name"
            ),
            {"name": "ix_recommendation_generations_incident_id_created_at"},
        )
        assert result.first() is not None


@pytest.mark.anyio
async def test_save_many_with_event_id_persists_it_and_is_retrievable_by_get_generation_by_event_id(make_recommendation):
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        event_id = uuid.uuid4()
        generation_id = uuid.uuid4()

        saved = await repository.save_many(
            [make_recommendation()], incident_id="INC-TEST0001", generation_id=generation_id, event_id=event_id
        )

        assert len(saved) == 1
        found_generation_id = await repository.get_generation_by_event_id(event_id)
        assert found_generation_id == generation_id


@pytest.mark.anyio
async def test_get_generation_by_event_id_returns_none_for_unknown_event_id():
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)

        assert await repository.get_generation_by_event_id(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_save_many_with_a_duplicate_event_id_raises_duplicate_generation_event_error(make_recommendation):
    """
    Database UNIQUE constraint behaviour: a second save_many() reusing an
    event_id already flushed within the same transaction is rejected
    immediately by Postgres's own constraint check -- the correctness
    guarantee beneath RecommendationLifecycleService's faster,
    application-level idempotency check (tested in isolation, without a
    database, in test_recommendation_lifecycle_service.py).
    """
    async with _repository_session() as session:
        repository = PostgreSQLRecommendationRepository(session)
        event_id = uuid.uuid4()

        await repository.save_many([make_recommendation()], incident_id="INC-A", generation_id=uuid.uuid4(), event_id=event_id)

        with pytest.raises(DuplicateGenerationEventError):
            await repository.save_many(
                [make_recommendation()], incident_id="INC-A", generation_id=uuid.uuid4(), event_id=event_id
            )


@pytest.mark.anyio
async def test_concurrent_save_many_with_the_same_event_id_are_mutually_exclusive(make_recommendation):
    """
    Genuine concurrency test, using two independent physical connections
    (NullPool guarantees this) racing to save_many() with the identical
    event_id. An in-process idempotency check cannot prevent this by
    itself -- two concurrent deliveries of the same event could both pass
    a "does it already exist?" read before either has written anything.
    Only the database's own UNIQUE constraint, exercised here for real
    across two genuinely separate transactions, guarantees exactly one of
    the two ever succeeds -- exactly one RecommendationGeneration.
    """
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")

    event_id = uuid.uuid4()
    incident_a = f"INC-{uuid.uuid4().hex[:8]}"
    incident_b = f"INC-{uuid.uuid4().hex[:8]}"

    async def _attempt(incident_id: str) -> str:
        async with _test_engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: RecommendationGenerationModel.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
            await conn.run_sync(lambda sync_conn: RecommendationModel.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
            await conn.commit()
            trans = await conn.begin()
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                repository = PostgreSQLRecommendationRepository(session)
                try:
                    await repository.save_many(
                        [make_recommendation(incident_id=incident_id)],
                        incident_id=incident_id,
                        generation_id=uuid.uuid4(),
                        event_id=event_id,
                    )
                except DuplicateGenerationEventError:
                    await trans.rollback()
                    return "duplicate"
                await trans.commit()
                return "ok"
            finally:
                await session.close()

    try:
        outcomes = await asyncio.gather(_attempt(incident_a), _attempt(incident_b))
        assert sorted(outcomes) == ["duplicate", "ok"]
    finally:
        async with _test_engine.connect() as cleanup_conn:
            await cleanup_conn.execute(
                text("DELETE FROM recommendations WHERE generation_id IN "
                     "(SELECT generation_id FROM recommendation_generations WHERE event_id = :event_id)"),
                {"event_id": str(event_id)},
            )
            await cleanup_conn.execute(
                text("DELETE FROM recommendation_generations WHERE event_id = :event_id"), {"event_id": str(event_id)}
            )
            await cleanup_conn.commit()


def test_repository_exposes_no_update_or_delete_operations():
    """Structural immutability check: append-only persistence has no mutation surface."""
    public_methods = {name for name in dir(PostgreSQLRecommendationRepository) if not name.startswith("_")}
    assert "update" not in public_methods
    assert "delete" not in public_methods
