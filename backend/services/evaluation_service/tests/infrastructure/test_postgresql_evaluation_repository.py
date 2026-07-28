"""
Repository tests: exercise `PostgreSQLEvaluationRepository` against a real
PostgreSQL database (no mocking of SQL execution) -- the only way to
genuinely verify JSONB persistence, the composite index, and real
save/query behavior. No automated-test DB infrastructure exists elsewhere
in this repository (every other service's tests use in-memory Fakes), so
these tests connect to `localhost:5432` (the same Postgres this project's
`docker compose up postgres` exposes) and skip cleanly, module-wide, if it
is not reachable -- `python -m pytest backend` remains green with or
without Docker running.

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

from backend.services.evaluation_service.app.domain.evaluation_repository import DuplicateEventError
from backend.services.evaluation_service.app.infrastructure.persistence.models.evaluation_model import EvaluationModel
from backend.services.evaluation_service.app.infrastructure.persistence.repositories.postgresql_evaluation_repository import (
    PostgreSQLEvaluationRepository,
)
from backend.shared.config.settings import Settings

# Independent, isolated engine pointed explicitly at localhost -- never
# reuses `backend.shared.database.database.engine` (which resolves to the
# Docker-network hostname "postgres" per this project's own .env, and is
# unreachable from the host process running pytest).
#
# `poolclass=NullPool`: each `@pytest.mark.anyio` test runs on its own,
# freshly-created event loop. A pooled connection opened during one test's
# loop is invalid once that loop closes -- reusing it from a later test
# crashes during asyncpg's cleanup (most visibly on Windows'
# ProactorEventLoop: "Event loop is closed"). NullPool opens a brand-new
# physical connection for every `.connect()` and closes it immediately
# after, so no connection is ever shared across event loop boundaries.
_test_settings = Settings(POSTGRES_HOST="localhost")
_test_engine = create_async_engine(_test_settings.database_url, poolclass=NullPool)

# Checked once and cached: re-attempting a fresh connection (and waiting
# out its connect timeout) for every single test would make the whole
# suite slow whenever Postgres isn't running, without adding any coverage.
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
    """
    Skips the calling test (via `pytest.skip`) if PostgreSQL is not
    reachable; otherwise ensures the `evaluations` table exists (idempotent
    -- mirrors the Alembic migration) and yields a session bound to a
    transaction that is rolled back on exit.
    """
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")

    async with _test_engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: EvaluationModel.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        # `run_sync` participates in the connection's autobegin transaction
        # (SQLAlchemy 2.0 default) -- commit it (the idempotent table
        # creation is meant to persist) before explicitly beginning the
        # transaction this test's own data changes will roll back.
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
async def test_save_persists_and_assigns_identity(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        evaluation = make_evaluation()

        record = await repository.save(evaluation)

        assert record.evaluation_id is not None
        assert record.created_at is not None
        assert record.evaluation.incident_id == evaluation.incident_id
        assert record.evaluation.quality_assessment == evaluation.quality_assessment
        assert record.evaluation.explainability_assessment == evaluation.explainability_assessment
        assert record.evaluation.confidence_summary == evaluation.confidence_summary


@pytest.mark.anyio
async def test_get_by_id_retrieves_a_saved_evaluation(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        saved = await repository.save(make_evaluation())

        fetched = await repository.get_by_id(saved.evaluation_id)

        assert fetched is not None
        assert fetched.evaluation_id == saved.evaluation_id
        assert fetched.evaluation == saved.evaluation


@pytest.mark.anyio
async def test_get_by_id_returns_none_for_unknown_id():
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)

        assert await repository.get_by_id(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_get_latest_returns_the_most_recently_saved_evaluation(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"

        await repository.save(make_evaluation(incident_id=incident_id))
        second = await repository.save(make_evaluation(incident_id=incident_id))

        latest = await repository.get_latest(incident_id)

        assert latest is not None
        assert latest.evaluation_id == second.evaluation_id


@pytest.mark.anyio
async def test_get_latest_returns_none_when_no_evaluations_exist():
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)

        assert await repository.get_latest(f"INC-{uuid.uuid4().hex[:8]}") is None


@pytest.mark.anyio
async def test_second_save_for_the_same_incident_links_previous_evaluation_id(make_evaluation):
    """History/lineage: append-only persistence chains new records to the prior one via previous_evaluation_id."""
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"

        first = await repository.save(make_evaluation(incident_id=incident_id))
        second = await repository.save(make_evaluation(incident_id=incident_id))

        assert first.evaluation.metadata.previous_evaluation_id is None
        assert second.evaluation.metadata.previous_evaluation_id == str(first.evaluation_id)


@pytest.mark.anyio
async def test_list_by_incident_filters_to_one_incident(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        incident_a = f"INC-{uuid.uuid4().hex[:8]}"
        incident_b = f"INC-{uuid.uuid4().hex[:8]}"

        await repository.save(make_evaluation(incident_id=incident_a))
        await repository.save(make_evaluation(incident_id=incident_b))

        results = await repository.list_by_incident(incident_a, limit=10, offset=0)

        assert len(results) == 1
        assert results[0].evaluation.incident_id == incident_a


@pytest.mark.anyio
async def test_list_by_incident_without_filter_spans_incidents(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        incident_a = f"INC-{uuid.uuid4().hex[:8]}"
        incident_b = f"INC-{uuid.uuid4().hex[:8]}"

        await repository.save(make_evaluation(incident_id=incident_a))
        await repository.save(make_evaluation(incident_id=incident_b))

        results = await repository.list_by_incident(None, limit=50, offset=0)
        incident_ids = {record.evaluation.incident_id for record in results}

        assert incident_a in incident_ids
        assert incident_b in incident_ids


@pytest.mark.anyio
async def test_list_by_incident_pagination_limit_and_offset(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        for _ in range(5):
            await repository.save(make_evaluation(incident_id=incident_id))

        first_page = await repository.list_by_incident(incident_id, limit=2, offset=0)
        second_page = await repository.list_by_incident(incident_id, limit=2, offset=2)

        assert len(first_page) == 2
        assert len(second_page) == 2
        assert {r.evaluation_id for r in first_page}.isdisjoint({r.evaluation_id for r in second_page})


@pytest.mark.anyio
async def test_list_history_returns_every_evaluation_for_an_incident(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        saved_ids = set()
        for _ in range(3):
            record = await repository.save(make_evaluation(incident_id=incident_id))
            saved_ids.add(record.evaluation_id)

        history = await repository.list_history(incident_id, limit=10, offset=0)

        assert {record.evaluation_id for record in history} == saved_ids


@pytest.mark.anyio
async def test_jsonb_fields_round_trip_through_real_postgres(make_evaluation):
    """
    Genuine JSONB persistence verification: findings/reasons are list-typed
    fields nested inside JSONB columns -- this proves PostgreSQL itself
    stores and returns them intact, which the pure-Python ORM mapping
    tests cannot prove on their own.
    """
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        evaluation = make_evaluation(
            root_cause_explanation="A" * 60, root_cause_evidence_count=5, business_impact_explanation="B" * 60
        )

        saved = await repository.save(evaluation)
        fetched = await repository.get_by_id(saved.evaluation_id)

        assert fetched is not None
        assert fetched.evaluation.quality_assessment.findings == evaluation.quality_assessment.findings
        assert (
            fetched.evaluation.explainability_assessment.findings == evaluation.explainability_assessment.findings
        )


@pytest.mark.anyio
async def test_composite_index_exists_on_incident_id_and_evaluation_version():
    async with _repository_session() as session:
        result = await session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'evaluations' AND indexname = :name"),
            {"name": "ix_evaluations_incident_id_evaluation_version"},
        )
        assert result.first() is not None


@pytest.mark.anyio
async def test_save_with_event_id_persists_it_and_is_retrievable_by_get_by_event_id(make_evaluation):
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        event_id = uuid.uuid4()

        saved = await repository.save(make_evaluation(), event_id=event_id)

        assert saved.event_id == event_id
        fetched = await repository.get_by_event_id(event_id)
        assert fetched is not None
        assert fetched.evaluation_id == saved.evaluation_id


@pytest.mark.anyio
async def test_get_by_event_id_returns_none_for_unknown_event_id():
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)

        assert await repository.get_by_event_id(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_save_with_a_duplicate_event_id_raises_duplicate_event_error(make_evaluation):
    """
    Database UNIQUE constraint behaviour: a second save() reusing an
    event_id already flushed within the same transaction is rejected
    immediately by Postgres's own constraint check -- the correctness
    guarantee beneath EvaluationLifecycleService's faster, application-level
    idempotency check (tested in isolation, without a database, in
    test_evaluation_lifecycle_service.py).
    """
    async with _repository_session() as session:
        repository = PostgreSQLEvaluationRepository(session)
        event_id = uuid.uuid4()

        await repository.save(make_evaluation(), event_id=event_id)

        with pytest.raises(DuplicateEventError):
            await repository.save(make_evaluation(), event_id=event_id)


@pytest.mark.anyio
async def test_concurrent_saves_with_the_same_event_id_are_mutually_exclusive(make_evaluation):
    """
    Genuine concurrency test, using two independent physical connections
    (NullPool guarantees this) racing to save() with the identical
    event_id. An in-process idempotency check cannot prevent this by
    itself -- two concurrent deliveries of the same event could both pass
    a "does it already exist?" read before either has written anything.
    Only the database's own UNIQUE constraint, exercised here for real
    across two genuinely separate transactions, guarantees exactly one of
    the two ever succeeds.
    """
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")

    event_id = uuid.uuid4()
    incident_a = f"INC-{uuid.uuid4().hex[:8]}"
    incident_b = f"INC-{uuid.uuid4().hex[:8]}"

    async def _attempt(incident_id: str) -> str:
        async with _test_engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: EvaluationModel.__table__.create(sync_conn, checkfirst=True))
            await conn.commit()
            trans = await conn.begin()
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                repository = PostgreSQLEvaluationRepository(session)
                try:
                    await repository.save(make_evaluation(incident_id=incident_id), event_id=event_id)
                except DuplicateEventError:
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
                text("DELETE FROM evaluations WHERE event_id = :event_id"), {"event_id": str(event_id)}
            )
            await cleanup_conn.commit()


def test_repository_exposes_no_update_or_delete_operations():
    """Structural immutability check: append-only persistence has no mutation surface."""
    public_methods = {name for name in dir(PostgreSQLEvaluationRepository) if not name.startswith("_")}
    assert "update" not in public_methods
    assert "delete" not in public_methods
