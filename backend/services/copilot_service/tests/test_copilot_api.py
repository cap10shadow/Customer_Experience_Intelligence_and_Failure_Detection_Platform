"""
Tests for `POST /api/v1/copilot/messages`'s HTTP-level contract
(request validation, conversation-id/request-id behavior, response
shape) and, as of Phase 12 Batch 4, real conversation persistence
behavior. As of Phase 12 Batch 3, the route runs the real bounded
orchestration graph; with no LLM provider configured in this test
environment (the default `NullLLMProvider`), it deterministically
produces one honest "no language model configured" answer with no tool
calls -- see `tests/test_orchestrator_graph.py` for tool-selection/
evidence/iteration-bound coverage using a scripted `FakeLLMProvider`.

Batch 4 makes every request go through a real `AsyncSession`
(`get_db_session`), so this whole module now needs a reachable
PostgreSQL instance -- connects to `localhost:5432` (the same Postgres
`docker compose up postgres` exposes) and skips cleanly, module-wide,
if it is not reachable, the same convention already established by
`recommendation_service`'s repository tests. Test rows are real,
committed rows (this exercises the real dependency-injected session,
not a rolled-back one) -- consistent with this prototype's "no
automatic expiry" persistence model (architecture §17); nothing here
depends on any other test's leftover rows.
"""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.copilot_service.app.main import app

import httpx

from backend.services.copilot_service.app.dependencies.http_client import get_http_client
from backend.services.copilot_service.app.models.conversation import CopilotConversation
from backend.services.copilot_service.app.models.message import CopilotMessage
from backend.shared.config.settings import Settings
from backend.shared.database.session import get_db_session

# Bare (non-`with`) TestClient never runs the app's lifespan, so
# `app.state.http_client` (constructed there) does not exist -- exactly
# like gateway_service's own tests, the dependency is overridden directly
# rather than requiring a live database for lifespan's own readiness
# check (Phase 12 Batch 3: the orchestrator's tool adapters need a real
# client parameter; these HTTP-contract tests don't need it to reach a
# real service, since the default NullLLMProvider never calls a tool).
app.dependency_overrides[get_http_client] = lambda: httpx.AsyncClient(
    transport=httpx.MockTransport(lambda request: httpx.Response(404))
)

# The app's own default DB session (backend.shared.database.session) is
# bound to `backend.shared.config.settings.settings`, which reads
# `POSTGRES_HOST=postgres` from the repository's `.env` (correct inside
# docker-compose, unreachable from a host-run test process) -- overridden
# here with a `localhost`-bound engine, exactly the same pattern
# `test_postgresql_recommendation_repository.py` already uses for its
# own standalone test engine.
#  `NullPool` (no connection reuse across requests) -- required here,
# not just tidy: `starlette.testclient.TestClient`'s portal binds each
# request to its own event loop, and a normal pooled asyncpg connection
# checked out on one loop cannot be reused on another (`RuntimeError:
# Event loop is closed`). Same reasoning as
# `test_postgresql_recommendation_repository.py`'s own standalone engine.
_test_settings = Settings(POSTGRES_HOST="localhost")
_test_engine = create_async_engine(_test_settings.database_url, poolclass=NullPool)
_test_session_maker = async_sessionmaker(_test_engine, expire_on_commit=False, autoflush=False)


async def _override_get_db_session():
    async with _test_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db_session] = _override_get_db_session


def _database_available() -> bool:
    async def _check() -> bool:
        try:
            async with _test_engine.connect() as probe:
                await probe.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    return asyncio.run(_check())


pytestmark = pytest.mark.skipif(
    not _database_available(),
    reason="PostgreSQL is not reachable on localhost:5432 -- run `docker compose up postgres` to enable these tests",
)

client = TestClient(app)


async def _fetch_conversation(conversation_id: str) -> CopilotConversation:
    async with _test_session_maker() as session:
        result = await session.execute(
            select(CopilotConversation).where(CopilotConversation.conversation_id == uuid.UUID(conversation_id))
        )
        return result.scalar_one()


async def _fetch_messages(conversation_id: str):
    async with _test_session_maker() as session:
        result = await session.execute(
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == uuid.UUID(conversation_id))
            .order_by(CopilotMessage.sequence)
        )
        return result.scalars().all()


def test_minimal_valid_request_returns_200_with_honest_no_provider_answer():
    response = client.post("/api/v1/copilot/messages", json={"message": "What is happening in West region?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == (
        "Copilot's language model is not configured in this environment, so this request cannot be interpreted."
    )


def test_missing_message_is_rejected():
    response = client.post("/api/v1/copilot/messages", json={})

    assert response.status_code == 422


def test_invalid_workspace_is_rejected():
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello", "workspace_context": {"workspace": "not-a-real-workspace"}},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "workspace", ["dashboard", "investigations", "recommendations", "analytics", "administration"]
)
def test_every_real_workspace_is_accepted(workspace):
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello", "workspace_context": {"workspace": workspace}},
    )

    assert response.status_code == 200


def test_unknown_top_level_field_is_rejected():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello", "unexpected_field": "value"})

    assert response.status_code == 422


def test_unknown_workspace_context_field_is_rejected():
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello", "workspace_context": {"workspace": "dashboard", "region": "west"}},
    )

    assert response.status_code == 422


def test_supplied_conversation_id_is_echoed_unchanged():
    supplied = str(uuid.uuid4())

    response = client.post("/api/v1/copilot/messages", json={"message": "hello", "conversation_id": supplied})

    assert response.json()["conversation_id"] == supplied


def test_absent_conversation_id_generates_a_valid_uuid():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    conversation_id = response.json()["conversation_id"]
    uuid.UUID(conversation_id)  # raises ValueError if not a valid UUID


def test_two_requests_without_a_conversation_id_get_different_ids():
    first = client.post("/api/v1/copilot/messages", json={"message": "hello"}).json()["conversation_id"]
    second = client.post("/api/v1/copilot/messages", json={"message": "hello"}).json()["conversation_id"]

    assert first != second


def test_response_shape_is_exactly_the_frozen_contract_no_more_no_less():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    body = response.json()
    assert set(body.keys()) == {
        "answer",
        "key_findings",
        "evidence_references",
        "related_entities",
        "visualization_hint",
        "limitations",
        "conversation_id",
        "request_id",
    }


def test_evidence_findings_and_entities_are_empty_and_visualization_hint_is_omitted():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    body = response.json()
    assert body["key_findings"] == []
    assert body["evidence_references"] == []
    assert body["related_entities"] == []
    assert body["visualization_hint"] is None


def test_limitations_honestly_state_no_llm_provider_is_configured():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})

    limitations = response.json()["limitations"]
    assert len(limitations) == 1
    assert "No LLM provider is configured" in limitations[0]


def test_x_request_id_is_echoed_as_request_id():
    response = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello"},
        headers={"X-Request-ID": "test-request-id-123"},
    )

    assert response.headers["X-Request-ID"] == "test-request-id-123"
    assert response.json()["request_id"] == "test-request-id-123"


def test_health_readiness_and_metrics_are_unaffected_by_the_new_route():
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200
    # /health/ready depends on a real database connection, which is not
    # necessarily available in this unit-test environment -- only assert
    # the route exists and returns a well-formed status, not a specific one.
    ready_response = client.get("/health/ready")
    assert ready_response.status_code in (200, 503)
    assert "status" in ready_response.json()


# --- Phase 12 Batch 4: conversation persistence -----------------------------------


def test_absent_conversation_id_persists_a_new_conversation_row():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})
    conversation_id = response.json()["conversation_id"]

    conversation = asyncio.run(_fetch_conversation(conversation_id))

    assert str(conversation.conversation_id) == conversation_id


def test_first_turn_persists_the_user_and_assistant_messages_in_order():
    response = client.post("/api/v1/copilot/messages", json={"message": "What is happening in West region?"})
    body = response.json()

    messages = asyncio.run(_fetch_messages(body["conversation_id"]))

    assert [m.role.value for m in messages] == ["user", "assistant"]
    assert messages[0].content == "What is happening in West region?"
    assert messages[1].content == body["answer"]
    assert messages[0].sequence < messages[1].sequence


def test_second_turn_with_the_same_conversation_id_appends_to_the_same_conversation():
    first = client.post("/api/v1/copilot/messages", json={"message": "hello"}).json()
    conversation_id = first["conversation_id"]

    second = client.post(
        "/api/v1/copilot/messages", json={"message": "why?", "conversation_id": conversation_id}
    ).json()

    messages = asyncio.run(_fetch_messages(conversation_id))
    assert [m.content for m in messages] == ["hello", first["answer"], "why?", second["answer"]]
    assert [m.sequence for m in messages] == sorted(m.sequence for m in messages)


def test_unrecognized_supplied_conversation_id_creates_a_conversation_under_that_id():
    supplied = str(uuid.uuid4())

    response = client.post("/api/v1/copilot/messages", json={"message": "hello", "conversation_id": supplied})

    assert response.json()["conversation_id"] == supplied
    conversation = asyncio.run(_fetch_conversation(supplied))
    assert str(conversation.conversation_id) == supplied
    messages = asyncio.run(_fetch_messages(supplied))
    assert len(messages) == 2


def test_workspace_context_is_snapshotted_only_on_conversation_creation():
    first = client.post(
        "/api/v1/copilot/messages",
        json={"message": "hello", "workspace_context": {"workspace": "dashboard"}},
    ).json()
    conversation_id = first["conversation_id"]

    client.post(
        "/api/v1/copilot/messages",
        json={
            "message": "follow up",
            "conversation_id": conversation_id,
            "workspace_context": {"workspace": "recommendations"},
        },
    )

    conversation = asyncio.run(_fetch_conversation(conversation_id))
    assert conversation.workspace == "dashboard"


def test_evidence_free_response_persists_null_evidence_references():
    response = client.post("/api/v1/copilot/messages", json={"message": "hello"})
    conversation_id = response.json()["conversation_id"]

    messages = asyncio.run(_fetch_messages(conversation_id))
    assistant_message = messages[-1]
    assert assistant_message.evidence_references is None


def test_orchestration_failure_persists_nothing_and_preserves_the_error_contract(monkeypatch):
    """
    Architecture §22 / Batch 4 implementation prompt §11: an assistant
    response must never be persisted as successful when orchestration
    itself fails, and the existing API error contract must not be lost.
    One session/transaction spans the whole turn (see
    `conversation_service.handle_persisted_query`'s docstring) -- an
    exception here must roll back the conversation-creation and the
    user-message append too, not just skip the assistant append.
    """
    import backend.services.copilot_service.app.services.conversation_service as conversation_service_module

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated orchestration failure")

    monkeypatch.setattr(conversation_service_module, "run_orchestration", _boom)

    # `raise_server_exceptions=False` (same convention as
    # `gateway_service/tests/test_errors.py`) so the TestClient returns
    # the real 500 response the registered `Exception` handler produces,
    # instead of re-raising the exception into the test itself.
    non_raising_client = TestClient(app, raise_server_exceptions=False)
    supplied = str(uuid.uuid4())
    response = non_raising_client.post(
        "/api/v1/copilot/messages", json={"message": "hello", "conversation_id": supplied}
    )

    assert response.status_code == 500

    async def _conversation_row_count() -> int:
        async with _test_session_maker() as session:
            result = await session.execute(
                select(CopilotConversation).where(CopilotConversation.conversation_id == uuid.UUID(supplied))
            )
            return len(result.scalars().all())

    assert asyncio.run(_conversation_row_count()) == 0
    assert asyncio.run(_fetch_messages(supplied)) == []
