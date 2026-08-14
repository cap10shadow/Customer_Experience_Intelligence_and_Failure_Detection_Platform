"""
Repository tests: exercise `CopilotConversationRepository`/
`CopilotMessageRepository` against a real PostgreSQL database (no
mocking of SQL execution) -- the only way to genuinely verify the
foreign key, the identity-column ordering guarantee, and real
save/query behavior. Connects to `localhost:5432` (the same Postgres
`docker compose up postgres` exposes) and skips cleanly, module-wide,
if it is not reachable -- `python -m pytest backend` remains green with
or without Docker running (same convention as
`recommendation_service/tests/infrastructure/test_postgresql_recommendation_repository.py`).

Every test runs inside a transaction that is always rolled back at the
end, so no test data is ever actually committed or left behind.
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.services.copilot_service.app.models.conversation import CopilotConversation
from backend.services.copilot_service.app.models.message import CopilotMessage
from backend.services.copilot_service.app.repositories.conversation_repository import CopilotConversationRepository
from backend.services.copilot_service.app.repositories.message_repository import CopilotMessageRepository
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference, WorkspaceContext
from backend.shared.config.settings import Settings
from backend.shared.constants.enums.copilot import CopilotMessageRole

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


# --- CopilotConversationRepository ------------------------------------------------


@pytest.mark.anyio
async def test_create_persists_conversation_with_context_snapshot():
    async with _repository_session() as session:
        repository = CopilotConversationRepository(session)
        conversation_id = uuid.uuid4()
        context = WorkspaceContext(workspace="investigations", incident_id="INC-1", recommendation_id="REC-1")

        created = await repository.create(conversation_id, workspace_context=context)

        assert created.conversation_id == conversation_id
        assert created.workspace == "investigations"
        assert created.incident_id == "INC-1"
        assert created.recommendation_id == "REC-1"


@pytest.mark.anyio
async def test_create_without_workspace_context_persists_null_fields():
    async with _repository_session() as session:
        repository = CopilotConversationRepository(session)
        conversation_id = uuid.uuid4()

        created = await repository.create(conversation_id, workspace_context=None)

        assert created.workspace is None
        assert created.incident_id is None
        assert created.recommendation_id is None


@pytest.mark.anyio
async def test_get_retrieves_a_saved_conversation():
    async with _repository_session() as session:
        repository = CopilotConversationRepository(session)
        conversation_id = uuid.uuid4()
        await repository.create(conversation_id, workspace_context=None)

        fetched = await repository.get(conversation_id)

        assert fetched is not None
        assert fetched.conversation_id == conversation_id


@pytest.mark.anyio
async def test_get_returns_none_for_unknown_id():
    async with _repository_session() as session:
        repository = CopilotConversationRepository(session)

        assert await repository.get(uuid.uuid4()) is None


@pytest.mark.anyio
async def test_touch_last_message_at_updates_timestamp():
    async with _repository_session() as session:
        repository = CopilotConversationRepository(session)
        conversation_id = uuid.uuid4()
        conversation = await repository.create(conversation_id, workspace_context=None)
        original = conversation.last_message_at

        await repository.touch_last_message_at(conversation)

        assert conversation.last_message_at >= original


# --- CopilotMessageRepository ------------------------------------------------


@pytest.mark.anyio
async def test_append_persists_user_and_assistant_messages():
    async with _repository_session() as session:
        conversation_repository = CopilotConversationRepository(session)
        message_repository = CopilotMessageRepository(session)
        conversation_id = uuid.uuid4()
        await conversation_repository.create(conversation_id, workspace_context=None)

        user_message = await message_repository.append(
            conversation_id=conversation_id, role=CopilotMessageRole.USER, content="What is happening?"
        )
        assistant_message = await message_repository.append(
            conversation_id=conversation_id, role=CopilotMessageRole.ASSISTANT, content="Here is the answer."
        )

        assert user_message.role == CopilotMessageRole.USER
        assert assistant_message.role == CopilotMessageRole.ASSISTANT
        assert user_message.conversation_id == conversation_id


@pytest.mark.anyio
async def test_append_stores_bounded_evidence_references_only():
    async with _repository_session() as session:
        conversation_repository = CopilotConversationRepository(session)
        message_repository = CopilotMessageRepository(session)
        conversation_id = uuid.uuid4()
        await conversation_repository.create(conversation_id, workspace_context=None)
        evidence = [
            EvidenceReference(
                evidence_id="E1", source_type="incident", source_id="INC-1", authority="anomaly_service", timestamp=None
            )
        ]

        message = await message_repository.append(
            conversation_id=conversation_id,
            role=CopilotMessageRole.ASSISTANT,
            content="answer",
            evidence_references=evidence,
        )

        assert message.evidence_references == [
            {"evidence_id": "E1", "source_type": "incident", "source_id": "INC-1", "authority": "anomaly_service", "timestamp": None}
        ]


@pytest.mark.anyio
async def test_append_without_evidence_references_stores_null():
    async with _repository_session() as session:
        conversation_repository = CopilotConversationRepository(session)
        message_repository = CopilotMessageRepository(session)
        conversation_id = uuid.uuid4()
        await conversation_repository.create(conversation_id, workspace_context=None)

        message = await message_repository.append(
            conversation_id=conversation_id, role=CopilotMessageRole.USER, content="hello"
        )

        assert message.evidence_references is None


@pytest.mark.anyio
async def test_list_recent_returns_messages_in_deterministic_sequence_order():
    async with _repository_session() as session:
        conversation_repository = CopilotConversationRepository(session)
        message_repository = CopilotMessageRepository(session)
        conversation_id = uuid.uuid4()
        await conversation_repository.create(conversation_id, workspace_context=None)

        expected_contents = [f"turn-{i}" for i in range(6)]
        for content in expected_contents:
            role = CopilotMessageRole.USER if len(content) % 2 == 0 else CopilotMessageRole.ASSISTANT
            await message_repository.append(conversation_id=conversation_id, role=role, content=content)

        history = await message_repository.list_recent(conversation_id)

        assert [m.content for m in history] == expected_contents


@pytest.mark.anyio
async def test_list_recent_bounded_by_limit_keeps_the_most_recent():
    async with _repository_session() as session:
        conversation_repository = CopilotConversationRepository(session)
        message_repository = CopilotMessageRepository(session)
        conversation_id = uuid.uuid4()
        await conversation_repository.create(conversation_id, workspace_context=None)

        for i in range(5):
            await message_repository.append(
                conversation_id=conversation_id, role=CopilotMessageRole.USER, content=f"turn-{i}"
            )

        history = await message_repository.list_recent(conversation_id, limit=2)

        assert [m.content for m in history] == ["turn-3", "turn-4"]


@pytest.mark.anyio
async def test_list_recent_for_unknown_conversation_returns_empty():
    async with _repository_session() as session:
        message_repository = CopilotMessageRepository(session)

        assert await message_repository.list_recent(uuid.uuid4()) == []


@pytest.mark.anyio
async def test_messages_are_scoped_to_their_own_conversation():
    async with _repository_session() as session:
        conversation_repository = CopilotConversationRepository(session)
        message_repository = CopilotMessageRepository(session)
        conversation_a = uuid.uuid4()
        conversation_b = uuid.uuid4()
        await conversation_repository.create(conversation_a, workspace_context=None)
        await conversation_repository.create(conversation_b, workspace_context=None)

        await message_repository.append(conversation_id=conversation_a, role=CopilotMessageRole.USER, content="a")
        await message_repository.append(conversation_id=conversation_b, role=CopilotMessageRole.USER, content="b")

        history_a = await message_repository.list_recent(conversation_a)

        assert [m.content for m in history_a] == ["a"]
