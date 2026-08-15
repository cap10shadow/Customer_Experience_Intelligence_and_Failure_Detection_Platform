from fastapi import Response
from starlette.requests import Request

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.errors import AuthenticationError
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.core.tokens import InvalidTokenError, create_access_token, decode_access_token

"""
The Gateway's authentication enforcement boundary (Phase 13 Batch 2,
AD-6 §9). `get_current_user` is the platform's first
`Depends(get_current_user)`-shaped dependency (AD-1 §7) -- every
protected route depends on this, never re-implements cookie/JWT
handling itself. This module owns the cookie's name and every one of
its attributes in exactly one place, so `POST /auth/login` (sets it)
and `POST /auth/logout` (clears it) can never drift out of sync with
each other or with what `get_current_user` expects to read.
"""

SESSION_COOKIE_NAME = "oi_session"


def _cookie_secure() -> bool:
    """
    §9: "Secure: yes in any non-localhost deployment... localhost gets
    browser leniency in dev." Rather than rely on that browser leniency
    (which would make local HTTP verification with tools that don't
    grant it, e.g. curl-over-network, silently fail to round-trip the
    cookie), this follows GatewaySettings.ENVIRONMENT explicitly --
    False only in local development, True the moment a real deployment
    sets ENVIRONMENT to anything else.
    """
    return settings.ENVIRONMENT != "development"


def set_session_cookie(response: Response, principal: AuthenticatedUser) -> None:
    token = create_access_token(principal)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Uses matching attributes to the ones set_session_cookie used -- a browser only honors a clearing Set-Cookie whose scoping attributes match the original."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )


def get_current_user(request: Request) -> AuthenticatedUser:
    """
    The dependency every protected route uses. Raises `AuthenticationError`
    (401, generic "Authentication required." message -- never a
    token/cookie fragment) for a missing cookie or an invalid/expired
    token; never falls back to trusting anything else about the request.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise AuthenticationError("Authentication required.")

    try:
        return decode_access_token(token)
    except InvalidTokenError as exc:
        raise AuthenticationError("Authentication required.") from exc
