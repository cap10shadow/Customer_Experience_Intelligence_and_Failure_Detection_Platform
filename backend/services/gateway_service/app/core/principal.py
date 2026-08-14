import uuid
from dataclasses import dataclass
from typing import Sequence

"""
The minimal authenticated-identity representation named by AD-1 (§7 of
the frozen architecture): "A minimal AuthenticatedUser (user_id, email,
roles) is the only representation of identity that crosses
gateway_service's authentication boundary; JWT implementation details
should remain inside that boundary and are never duplicated in
downstream services."

Batch 1 defines the plain value object only. Nothing in this batch
constructs one from a real request -- there is no login flow, no JWT
validation, and no FastAPI dependency wiring this into a route yet.
That is Batch 3 (Authentication API) and Batch 4 (RBAC enforcement)
scope. This type exists now so those later batches depend on an
already-reviewed shape rather than inventing one under time pressure.
"""


@dataclass(frozen=True)
class AuthenticatedUser:
    """An immutable snapshot of the caller's identity, once resolved by a future Batch 3 JWT-validation dependency."""

    user_id: uuid.UUID
    email: str
    roles: Sequence[str]
