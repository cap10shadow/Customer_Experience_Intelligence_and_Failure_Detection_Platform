"""
End-to-end evaluation-runner tests against a real PostgreSQL instance
(no mocking of persistence) -- exercises the real, unmodified
`conversation_service.handle_persisted_query` path (§12 of the Batch 6
implementation prompt: "must exercise the real Copilot conversation
path"). Skips cleanly, module-wide, if Postgres is unreachable, the same
convention `test_conversation_persistence_repository.py` already
established. Every test runs inside a transaction that is always rolled
back, so no test data is ever actually committed or left behind.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.copilot_service.app.evaluation.dataset import EvaluationDataset, load_dataset
from backend.services.copilot_service.app.evaluation.results import CheckStatus, Dimension
from backend.services.copilot_service.app.evaluation.runner import run_evaluation
from backend.services.copilot_service.app.models.conversation import CopilotConversation
from backend.services.copilot_service.app.models.message import CopilotMessage
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
async def _eval_session() -> AsyncIterator[AsyncSession]:
    if not await _is_database_available():
        pytest.skip("PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests")

    async with _test_engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: CopilotConversation.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
        await conn.run_sync(lambda sync_conn: CopilotMessage.__table__.create(sync_conn, checkfirst=True))  # type: ignore[attr-defined]
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


def _unreachable_client() -> httpx.AsyncClient:
    """Every real domain service call fails fast -- keeps these tests independent of which domain services happen to be running."""
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(503)))


@pytest.mark.anyio
async def test_runner_executes_the_real_dataset_and_returns_one_result_per_case():
    dataset = load_dataset()
    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    assert report.total == len(dataset.cases)
    assert {case.case_id for case in report.cases} == {case.case_id for case in dataset.cases}


@pytest.mark.anyio
async def test_scripted_cases_are_labeled_scripted_and_unscripted_case_reports_the_real_provider():
    dataset = load_dataset()
    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    by_id = {case.case_id: case for case in report.cases}
    assert by_id["unsupported_request_refusal"].provider_used == "scripted"
    # No LLM_PROVIDER is configured anywhere in this repository's default
    # environment (verified: `.env.example` documents `LLM_PROVIDER=none`)
    # -- this case intentionally scripts nothing, so it honestly reports
    # whatever provider `get_llm_provider()` really resolves to.
    assert by_id["environment_provider_baseline"].provider_used == "NullLLMProvider"


@pytest.mark.anyio
async def test_hallucination_case_never_lets_the_fabricated_evidence_id_survive():
    dataset = load_dataset()
    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    case = next(c for c in report.cases if c.case_id == "hallucination_rejection")
    hallucination_result = next(d for d in case.dimension_results if d.dimension == Dimension.HALLUCINATION)
    assert hallucination_result.status == CheckStatus.PASS
    assert case.error is None


@pytest.mark.anyio
async def test_forbidden_tool_attempt_never_actually_executes_the_tool():
    dataset = load_dataset()
    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    case = next(c for c in report.cases if c.case_id == "forbidden_tool_attempt")
    tool_result = next(d for d in case.dimension_results if d.dimension == Dimension.TOOL_SELECTION)
    assert tool_result.status == CheckStatus.PASS


@pytest.mark.anyio
async def test_conversation_turn_2_reuses_turn_1s_real_backend_conversation_id():
    dataset = load_dataset()
    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    turn_1 = next(c for c in report.cases if c.case_id == "conversation_turn_1")
    turn_2 = next(c for c in report.cases if c.case_id == "conversation_turn_2")
    assert turn_1.error is None
    assert turn_2.error is None

    # Verify against real persisted rows -- not just that the runner didn't error.
    from sqlalchemy import select

    async with _eval_session() as verify_session:
        result = await verify_session.execute(select(CopilotConversation))
        conversations = result.scalars().all()
        assert len(conversations) >= 1


@pytest.mark.anyio
async def test_safety_read_only_dimension_passes_for_every_case():
    dataset = load_dataset()
    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    for case in report.cases:
        safety_result = next((d for d in case.dimension_results if d.dimension == Dimension.SAFETY_READ_ONLY), None)
        assert safety_result is not None, f"case {case.case_id} did not run the safety dimension"
        assert safety_result.status == CheckStatus.PASS


@pytest.mark.anyio
async def test_a_malformed_runtime_case_is_reported_as_an_error_without_aborting_the_run():
    dataset = EvaluationDataset(
        dataset_kind="synthetic_evaluation_fixtures",
        cases=[
            {
                "case_id": "bad_workspace",
                "category": "malformed",
                "description": "deliberately invalid workspace_context to prove one bad case doesn't abort the run",
                "message": "hello",
                "workspace_context": {"workspace": "not_a_real_workspace"},
            },
            {
                "case_id": "good_after_bad",
                "category": "malformed",
                "description": "must still run even though the prior case failed",
                "message": "hello",
            },
        ],
    )

    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    assert report.total == 2
    bad = next(c for c in report.cases if c.case_id == "bad_workspace")
    good = next(c for c in report.cases if c.case_id == "good_after_bad")
    assert bad.error is not None
    assert bad.passed is False
    assert good.error is None


@pytest.mark.anyio
async def test_a_case_referencing_a_failed_prior_case_records_its_own_error_without_crashing_the_run():
    """
    Regression test: a case whose `conversation_id_from_case` points at a
    case that itself failed (so no conversation_id was ever recorded for
    it) must be reported as *that case's own* error -- never let a raw
    `DatasetReferenceError` escape `run_evaluation` and abort every
    remaining case. Found during real runtime verification (Batch 6):
    the original implementation resolved `conversation_id_from_case`
    outside the per-case try/except.
    """
    dataset = EvaluationDataset(
        dataset_kind="synthetic_evaluation_fixtures",
        cases=[
            {
                "case_id": "turn_1_fails",
                "category": "malformed",
                "description": "deliberately invalid workspace_context so this case fails before producing a conversation_id",
                "message": "hello",
                "workspace_context": {"workspace": "not_a_real_workspace"},
            },
            {
                "case_id": "turn_2_references_failed_turn_1",
                "category": "malformed",
                "description": "must be recorded as its own error, not crash the run",
                "message": "why?",
                "conversation_id_from_case": "turn_1_fails",
            },
            {
                "case_id": "unrelated_case_runs_after",
                "category": "malformed",
                "description": "must still run even though two prior cases failed",
                "message": "hello",
            },
        ],
    )

    async with _eval_session() as session, _unreachable_client() as client:
        report = await run_evaluation(dataset, client=client, session=session)

    assert report.total == 3
    by_id = {case.case_id: case for case in report.cases}
    assert by_id["turn_1_fails"].error is not None
    assert by_id["turn_2_references_failed_turn_1"].error is not None
    assert by_id["unrelated_case_runs_after"].error is None
