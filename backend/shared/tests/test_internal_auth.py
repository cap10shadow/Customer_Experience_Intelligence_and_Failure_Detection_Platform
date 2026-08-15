"""
Pure unit tests for the internal service-to-service credential
primitive (Phase 13 Batch 4, AD-5). No HTTP, no database -- calls
`require_internal_secret` directly with an explicit header value,
matching this repo's convention of testing a FastAPI dependency
function's own logic in isolation.
"""

import pytest
from fastapi import HTTPException

from backend.shared.config.settings import settings
from backend.shared.security.internal_auth import (
    INTERNAL_SECRET_HEADER,
    PRINCIPAL_USER_ID_HEADER,
    internal_service_headers,
    require_internal_secret,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_the_correct_secret_passes():
    await require_internal_secret(x_internal_secret=settings.INTERNAL_SERVICE_SECRET)


@pytest.mark.anyio
async def test_a_missing_secret_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await require_internal_secret(x_internal_secret=None)

    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_an_empty_secret_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await require_internal_secret(x_internal_secret="")

    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_an_incorrect_secret_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await require_internal_secret(x_internal_secret="the-wrong-secret")

    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_missing_and_wrong_secret_produce_the_identical_error_detail():
    """Fail-closed, generic: a client must not be able to distinguish 'missing' from 'wrong' from the response."""
    with pytest.raises(HTTPException) as missing_exc:
        await require_internal_secret(x_internal_secret=None)
    with pytest.raises(HTTPException) as wrong_exc:
        await require_internal_secret(x_internal_secret="the-wrong-secret")

    assert missing_exc.value.detail == wrong_exc.value.detail
    assert missing_exc.value.status_code == wrong_exc.value.status_code


@pytest.mark.anyio
async def test_the_rejection_never_includes_the_real_configured_secret():
    with pytest.raises(HTTPException) as exc_info:
        await require_internal_secret(x_internal_secret="wrong")

    assert settings.INTERNAL_SERVICE_SECRET not in str(exc_info.value.detail)


def test_internal_service_headers_uses_the_exact_documented_header_name():
    headers = internal_service_headers()

    assert headers == {INTERNAL_SECRET_HEADER: settings.INTERNAL_SERVICE_SECRET}
    assert INTERNAL_SECRET_HEADER == "X-Internal-Secret"


def test_principal_header_name_is_exactly_as_documented():
    assert PRINCIPAL_USER_ID_HEADER == "X-Authenticated-User-Id"
