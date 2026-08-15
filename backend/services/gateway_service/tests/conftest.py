import uuid

import pytest

from backend.services.gateway_service.app.core.auth_dependency import get_current_user
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.main import app

TEST_PRINCIPAL = AuthenticatedUser(user_id=uuid.uuid4(), email="test-user@example.com", roles=[])


@pytest.fixture(autouse=True)
def _authenticated_by_default():
    """
    Phase 13 Batch 2 (AD-6): every one of the 6 business routers
    (dashboard/investigations/recommendations/analytics/administration/
    copilot) now requires a valid session (main.py). The pre-existing
    test suite for those routers predates authentication and exercises
    aggregation logic, not the auth boundary itself -- overriding
    `get_current_user` here (FastAPI's own dependency-override
    mechanism, not a patched module) keeps those tests verifying
    exactly what they always verified, with zero per-test changes.

    `test_auth_api.py`'s own tests pop this override at the start of
    each test that must exercise real 401/authenticated-session
    behavior; this fixture's teardown restores it afterward regardless.
    """
    app.dependency_overrides[get_current_user] = lambda: TEST_PRINCIPAL
    yield
    app.dependency_overrides.pop(get_current_user, None)
