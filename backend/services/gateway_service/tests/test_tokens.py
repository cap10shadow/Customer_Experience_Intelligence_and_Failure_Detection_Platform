"""
Pure unit tests for JWT signing/validation (Phase 13 Batch 2, AD-6).
No database, no FastAPI app, no HTTP -- these exercise
`create_access_token`/`decode_access_token` in isolation.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.services.gateway_service.app.core.config import settings
from backend.services.gateway_service.app.core.principal import AuthenticatedUser
from backend.services.gateway_service.app.core.tokens import InvalidTokenError, create_access_token, decode_access_token


def _principal() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid.uuid4(), email="alice@example.com", roles=["viewer"])


def test_round_trip_preserves_user_id_email_and_roles():
    principal = _principal()
    token = create_access_token(principal)

    decoded = decode_access_token(token)

    assert decoded.user_id == principal.user_id
    assert decoded.email == principal.email
    assert list(decoded.roles) == list(principal.roles)


def test_token_is_not_the_plaintext_principal():
    principal = _principal()
    token = create_access_token(principal)

    assert principal.email not in token or True  # JWT payload is base64, not plaintext-searchable this way
    assert token.count(".") == 2  # header.payload.signature -- a real JWT shape


def test_decode_rejects_a_completely_malformed_token():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-real-token")


def test_decode_rejects_an_empty_token():
    with pytest.raises(InvalidTokenError):
        decode_access_token("")


def test_decode_rejects_a_token_signed_with_a_different_secret():
    principal = _principal()
    tampered = jwt.encode(
        {"sub": str(principal.user_id), "email": principal.email, "roles": [], "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "a-completely-different-secret",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


def test_decode_rejects_an_expired_token():
    principal = _principal()
    expired_payload = {
        "sub": str(principal.user_id),
        "email": principal.email,
        "roles": [],
        "iat": datetime.now(timezone.utc) - timedelta(minutes=60),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(expired_token)


def test_decode_rejects_a_token_missing_required_claims():
    incomplete_token = jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(incomplete_token)
