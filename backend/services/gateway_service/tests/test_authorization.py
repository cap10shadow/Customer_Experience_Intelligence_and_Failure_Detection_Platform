"""
Unit tests for `require_role()` (Phase 13 Batch 3, §11/§12). Calls the
returned dependency directly with an explicit `AuthenticatedUser` --
bypassing FastAPI's dependency injection and `get_current_user`
entirely, matching this repo's convention of testing a dependency
factory's own logic in isolation (`require_role`'s ordering guarantee
against a missing/invalid session is instead verified at the
integration level in `test_auth_api.py`/`test_rbac_api.py`, since that
depends on real cookie/JWT handling).
"""

import uuid

import pytest

from backend.services.gateway_service.app.core.authorization import require_role
from backend.services.gateway_service.app.core.errors import AuthorizationError
from backend.services.gateway_service.app.core.principal import AuthenticatedUser


def _principal(*roles: str) -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid.uuid4(), email="test@example.com", roles=list(roles))


def test_require_role_returns_the_principal_when_the_role_is_sufficient():
    dependency = require_role("viewer")

    result = dependency(_principal("viewer"))

    assert result.email == "test@example.com"


def test_require_role_raises_authorization_error_when_the_role_is_insufficient():
    dependency = require_role("operator")

    with pytest.raises(AuthorizationError) as exc_info:
        dependency(_principal("viewer"))

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_require_role_raises_for_a_principal_with_no_roles_at_all():
    dependency = require_role("viewer")

    with pytest.raises(AuthorizationError):
        dependency(_principal())


def test_require_role_error_message_never_names_the_required_or_actual_roles():
    dependency = require_role("admin")

    with pytest.raises(AuthorizationError) as exc_info:
        dependency(_principal("viewer", "operator"))

    message = exc_info.value.message
    assert "admin" not in message
    assert "viewer" not in message
    assert "operator" not in message


def test_admin_satisfies_an_operator_requirement():
    dependency = require_role("operator")

    result = dependency(_principal("admin"))

    assert result is not None
