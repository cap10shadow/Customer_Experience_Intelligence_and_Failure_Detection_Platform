from typing import Optional

from backend.services.gateway_service.app.core.security import verify_password
from backend.services.gateway_service.app.models.identity import User
from backend.services.gateway_service.app.repositories.identity_repository import UserRepository

"""
Credential verification (Phase 13 Batch 2). Reuses Batch 1's
`verify_password` primitive verbatim -- no password-hashing logic is
duplicated here.
"""


async def authenticate(user_repository: UserRepository, *, email: str, password: str) -> Optional[User]:
    """
    Returns the `User` if `email`/`password` are a valid, active
    credential pair; `None` for every failure mode (unknown email,
    wrong password, inactive user) -- deliberately undifferentiated, so
    a caller can never accidentally leak which failure occurred (AD-6
    §10: "do not reveal whether an account exists through materially
    different error semantics").
    """
    user = await user_repository.get_by_email(email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
