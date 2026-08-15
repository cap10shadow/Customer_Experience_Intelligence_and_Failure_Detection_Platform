import uuid

import pytest

from backend.services.gateway_service.app.core.auth_dependency import get_current_user
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.main import app

# Phase 13 Batch 3 (RBAC, §11): "admin" is the top of the role
# hierarchy (roles.py), so this single fixed principal satisfies every
# viewer/operator/admin requirement any router or route might carry --
# the pre-existing test suite this fixture serves predates RBAC and
# exercises aggregation logic, not role differentiation, so it should
# never observe a 403 regardless of which capability it happens to call.
TEST_PRINCIPAL = AuthenticatedUser(user_id=uuid.uuid4(), email="test-user@example.com", roles=["admin"])


@pytest.fixture(autouse=True)
def _authenticated_by_default():
    """
    Phase 13 Batch 2 (AD-6) introduced session enforcement; Batch 3
    (RBAC) layered role enforcement on top of it via the same
    `get_current_user` dependency (every `require_role(...)` check
    depends on it internally, so overriding it here transitively
    satisfies both). The pre-existing test suite for the 6 business
    routers predates both and exercises aggregation logic, not the
    auth/authz boundary itself -- overriding `get_current_user` here
    (FastAPI's own dependency-override mechanism, not a patched module)
    keeps those tests verifying exactly what they always verified, with
    zero per-test changes.

    `test_auth_api.py`/`test_rbac_api.py`'s own tests pop this override
    at the start of each test that must exercise real
    401/403/authenticated-session behavior; this fixture's teardown
    restores it afterward regardless.
    """
    app.dependency_overrides[get_current_user] = lambda: TEST_PRINCIPAL
    yield
    app.dependency_overrides.pop(get_current_user, None)
