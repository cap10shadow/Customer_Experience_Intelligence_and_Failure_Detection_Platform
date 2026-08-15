from typing import Callable

from fastapi import Depends

from backend.services.gateway_service.app.core.auth_dependency import get_current_user
from backend.services.gateway_service.app.core.errors import AuthorizationError
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.core.roles import has_sufficient_role

"""
The Gateway's role-based authorization boundary (Phase 13 Batch 3 --
frozen architecture §11/§12). Deliberately a separate module from
`auth_dependency.py`: authentication ("who is this?") and authorization
("are they allowed to do this?") are two different questions, per the
frozen architecture's own explicit instruction not to conflate them.

This is the ONE reusable authorization primitive in the platform --
every route that needs a role check depends on `require_role(...)`,
never a hand-rolled role comparison. The authenticated principal always
comes from `get_current_user` (Batch 2's trusted, server-validated JWT
claims) -- never from a request body, query/path parameter, header, or
any other client-suppliable input, so a client can never elevate its
own privileges by claiming a role.
"""


def require_role(minimum_role: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """
    Returns a FastAPI dependency enforcing `minimum_role` (per the
    hierarchy in `roles.py`) against the authenticated principal.

    Ordering matters: this depends on `get_current_user`, so a missing
    or invalid session is always resolved (and raises 401) before any
    role comparison happens -- a request can never receive a 403
    without first having a genuinely valid, authenticated session. An
    authenticated session lacking the required role raises
    `AuthorizationError` (403), never 401.
    """

    def _check_role(principal: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not has_sufficient_role(principal.roles, minimum_role):
            raise AuthorizationError("You do not have permission to perform this action.")
        return principal

    return _check_role
