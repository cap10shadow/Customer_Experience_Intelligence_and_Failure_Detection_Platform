"""
Unit tests for `authenticate()` (Phase 13 Batch 2) against a fake,
in-memory `UserRepository` -- no database, no HTTP. Real password
hashing (Batch 1's `hash_password`) is exercised for real; only
persistence is faked.
"""

import uuid
from typing import Optional

import pytest

from backend.services.gateway_service.app.core.security import hash_password
from backend.services.gateway_service.app.models.identity import User
from backend.services.gateway_service.app.services.auth_service import authenticate


class _FakeUserRepository:
    def __init__(self, users: list[User]):
        self._users = {user.email: user for user in users}

    async def get_by_email(self, email: str) -> Optional[User]:
        return self._users.get(email)


def _make_user(*, email: str, password: str, is_active: bool = True) -> User:
    user = User(id=uuid.uuid4(), email=email, password_hash=hash_password(password), is_active=is_active)
    return user


@pytest.mark.anyio
async def test_authenticate_returns_the_user_for_correct_credentials():
    user = _make_user(email="alice@example.com", password="correct-password")
    repository = _FakeUserRepository([user])

    result = await authenticate(repository, email="alice@example.com", password="correct-password")

    assert result is not None
    assert result.email == "alice@example.com"


@pytest.mark.anyio
async def test_authenticate_returns_none_for_unknown_email():
    repository = _FakeUserRepository([])

    result = await authenticate(repository, email="nobody@example.com", password="anything")

    assert result is None


@pytest.mark.anyio
async def test_authenticate_returns_none_for_wrong_password():
    user = _make_user(email="bob@example.com", password="the-real-password")
    repository = _FakeUserRepository([user])

    result = await authenticate(repository, email="bob@example.com", password="a-wrong-password")

    assert result is None


@pytest.mark.anyio
async def test_authenticate_returns_none_for_an_inactive_user_even_with_the_correct_password():
    user = _make_user(email="carol@example.com", password="correct-password", is_active=False)
    repository = _FakeUserRepository([user])

    result = await authenticate(repository, email="carol@example.com", password="correct-password")

    assert result is None


@pytest.fixture
def anyio_backend():
    return "asyncio"
