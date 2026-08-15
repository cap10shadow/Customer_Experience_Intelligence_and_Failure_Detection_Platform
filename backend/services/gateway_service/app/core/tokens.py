import uuid
from datetime import datetime, timedelta, timezone

import jwt

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.principal import AuthenticatedUser

"""
Session/token signing and validation (Phase 13 Batch 2, AD-1 §7 / AD-6).
This module is deliberately the platform's only place that touches raw
JWT claims -- everything else works with the plain `AuthenticatedUser`
value object (§7: "JWT implementation details should remain inside the
authentication boundary... and are never duplicated in downstream
services"). No refresh-token logic, no OAuth, no MFA -- explicitly
deferred (§30 of the frozen architecture).
"""

_SUBJECT_CLAIM = "sub"
_EMAIL_CLAIM = "email"
_ROLES_CLAIM = "roles"


class InvalidTokenError(Exception):
    """Raised for any missing/malformed/expired/tampered token -- never distinguishes which, matching AD-6's generic-failure discipline."""


def create_access_token(principal: AuthenticatedUser) -> str:
    """
    Issues a short-lived (`JWT_EXPIRE_MINUTES`) signed JWT carrying only
    the `AuthenticatedUser` shape (§7: user_id/email/roles) plus standard
    `iat`/`exp` claims. No refresh token, no session-database row -- the
    JWT itself, once expired, is the platform's only session-length
    control in this batch (AD-6).
    """
    now = datetime.now(timezone.utc)
    payload = {
        _SUBJECT_CLAIM: str(principal.user_id),
        _EMAIL_CLAIM: principal.email,
        _ROLES_CLAIM: list(principal.roles),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> AuthenticatedUser:
    """
    Validates signature and expiry, then reconstructs the
    `AuthenticatedUser` the token was issued for. Raises
    `InvalidTokenError` (never a raw `jwt.*` exception) for every
    failure mode -- missing claim, bad signature, expiry, or malformed
    token -- so callers have exactly one exception type to handle.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return AuthenticatedUser(
            user_id=uuid.UUID(payload[_SUBJECT_CLAIM]),
            email=payload[_EMAIL_CLAIM],
            roles=payload.get(_ROLES_CLAIM, []),
        )
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise InvalidTokenError("The session token is missing, malformed, or expired.") from exc
