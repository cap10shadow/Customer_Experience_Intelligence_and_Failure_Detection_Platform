"""
Pure unit tests for the password hashing primitive (Phase 13 Batch 1,
AD-1). No database, no FastAPI app -- these exercise
`hash_password`/`verify_password` in isolation.
"""

from backend.services.gateway_service.app.core.security import hash_password, verify_password


def test_hash_password_is_not_plaintext():
    password = "correct horse battery staple"
    hashed = hash_password(password)

    assert hashed != password
    assert password not in hashed


def test_hash_password_produces_a_bcrypt_hash():
    hashed = hash_password("some-password")

    # bcrypt's own standard encoding prefix ($2a$/$2b$/$2y$ + cost factor).
    assert hashed.startswith("$2")


def test_hash_password_is_salted_and_nondeterministic():
    password = "same-password"

    first = hash_password(password)
    second = hash_password(password)

    assert first != second


def test_verify_password_accepts_the_correct_password():
    password = "hunter2-is-a-bad-password-but-a-fine-test-fixture"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_rejects_the_wrong_password():
    hashed = hash_password("the-real-password")

    assert verify_password("a-completely-different-password", hashed) is False


def test_verify_password_rejects_an_empty_password_against_a_real_hash():
    hashed = hash_password("the-real-password")

    assert verify_password("", hashed) is False


def test_verify_password_returns_false_for_a_malformed_hash_rather_than_raising():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False
