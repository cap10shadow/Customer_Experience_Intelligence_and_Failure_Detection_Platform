from fastapi import APIRouter, Depends, Response, status

from backend.services.gateway_service.app.core.auth_dependency import (
    clear_session_cookie,
    get_current_user,
    set_session_cookie,
)
from backend.services.gateway_service.app.core.errors import AuthenticationError
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.dependencies.repositories import RoleRepo, UserRepo
from backend.services.gateway_service.app.schemas.auth import AuthenticatedUserResponse, LoginRequest
from backend.services.gateway_service.app.services.auth_service import authenticate

"""
Phase 13 Batch 2 (AD-6 §9/§10): the platform's public authentication
API -- exactly the three routes the frozen architecture names, no more
(no /register, /refresh, /password-reset, /verify-email, /mfa, /oauth,
/sso -- all explicitly deferred).
"""

router = APIRouter(tags=["auth"])


def _to_response(principal: AuthenticatedUser) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse(userId=str(principal.user_id), email=principal.email, roles=list(principal.roles))


@router.post("/auth/login", response_model=AuthenticatedUserResponse)
async def login(
    request: LoginRequest,
    response: Response,
    user_repository: UserRepo,
    role_repository: RoleRepo,
) -> AuthenticatedUserResponse:
    """
    Verifies credentials, issues the HttpOnly session cookie, and
    returns the authenticated principal. Unknown email, wrong password,
    and an inactive user all raise the exact same `AuthenticationError`
    ("Invalid email or password.") -- AD-6's generic-failure discipline,
    so no response distinguishes which case occurred.
    """
    user = await authenticate(user_repository, email=request.email, password=request.password)
    if user is None:
        raise AuthenticationError("Invalid email or password.")

    roles = await role_repository.list_for_user(user.id)
    principal = AuthenticatedUser(user_id=user.id, email=user.email, roles=[role.name for role in roles])

    await user_repository.touch_last_login(user.id)
    set_session_cookie(response, principal)

    return _to_response(principal)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """
    Clears the session cookie. Deliberately does not require an
    authenticated session itself -- logout is idempotent: clearing a
    cookie that was already missing or expired is harmless, and
    requiring authentication here would make an already-expired
    session's browser unable to ever clear its own stale cookie.

    Mutates the injected `response` and returns `None` rather than
    constructing a fresh `Response(...)` -- returning a route's own new
    Response object discards whatever headers were already set on the
    injected one, which would silently drop the clearing Set-Cookie
    header entirely.
    """
    clear_session_cookie(response)


@router.get("/auth/me", response_model=AuthenticatedUserResponse)
async def get_current_authenticated_user(
    principal: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUserResponse:
    """Requires a valid session (`get_current_user` raises 401 otherwise); returns exactly what the session claims -- never anything read from the request body/query."""
    return _to_response(principal)
