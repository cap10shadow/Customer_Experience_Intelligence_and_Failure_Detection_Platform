import bcrypt

"""
Password hashing/verification primitive (Phase 13 Batch 1, AD-1 --
docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md §7/§8; §11 of
docs/DECISIONS.md's AD-1: "PASSWORDS MUST NEVER BE STORED IN
PLAINTEXT"). This module is deliberately the platform's only place
that touches a raw password -- callers pass a plaintext password in,
get an opaque hash out, and never see or log the plaintext again.

Batch 1 scope only: this is the reusable primitive, not the login
flow. Nothing in this module issues a session, a JWT, or a cookie --
that is Batch 3 (Authentication API) scope.
"""


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password with bcrypt (a per-call random salt is
    generated automatically by `bcrypt.gensalt()` and embedded in the
    returned hash, matching bcrypt's own standard encoding). The
    plaintext password is never logged or persisted anywhere -- only
    the returned hash is ever stored (`User.password_hash`).
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifies a plaintext password against a previously hashed value.
    Returns False (never raises) for a malformed/foreign hash, so a
    corrupted `password_hash` value can never crash a caller -- it can
    only ever fail to verify.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
