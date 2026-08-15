"""
Shared, non-test helper (no `test_` prefix -- pytest will not collect
it) for Phase 13 Batch 6 Copilot ownership tests.
`copilot_conversations.owner_id` now carries a real, cross-service
database-level FOREIGN KEY to gateway_service's `users.id` (AD-4, §17)
-- any test exercising a real, non-null `owner_id` against a migrated
database must first ensure a matching `users` row exists, the same
precedent already established by
`recommendation_service/tests/infrastructure/test_postgresql_recommendation_repository.py
._insert_test_user` for Phase 13 Batch 5's `decided_by`/`actor_id`.

Two fixed, well-known UUIDs (not `uuid.uuid4()` per test) so
`ensure_test_owner_exists`/`ensure_other_owner_exists` stay idempotent
(`ON CONFLICT DO NOTHING`) across repeated runs of the same test module,
whether the caller commits for real (`test_copilot_api.py`) or rolls
back (`test_conversation_persistence_repository.py`,
`test_evaluation_runner.py`).
"""

import uuid

from sqlalchemy import text

TEST_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
TEST_OWNER_EMAIL = "copilot-test-owner-a@test.invalid"

TEST_OTHER_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a2")
TEST_OTHER_OWNER_EMAIL = "copilot-test-owner-b@test.invalid"


async def _upsert_user(conn, user_id: uuid.UUID, email: str) -> None:
    await conn.execute(
        text(
            "INSERT INTO users (id, email, password_hash, is_active) "
            "VALUES (:id, :email, :password_hash, TRUE) ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(user_id), "email": email, "password_hash": "not-a-real-hash"},
    )


async def ensure_test_owner_exists(conn) -> None:
    """`conn` may be an `AsyncSession` or an `AsyncConnection` -- both support `.execute()`."""
    await _upsert_user(conn, TEST_OWNER_ID, TEST_OWNER_EMAIL)


async def ensure_other_owner_exists(conn) -> None:
    await _upsert_user(conn, TEST_OTHER_OWNER_ID, TEST_OTHER_OWNER_EMAIL)
