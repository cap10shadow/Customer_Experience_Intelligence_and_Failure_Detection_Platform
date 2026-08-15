from typing import List

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """
    POST /api/v1/auth/login body. `email` is a plain `str`, not
    Pydantic's `EmailStr` -- that type requires the optional
    `email-validator` package, an extra dependency this batch doesn't
    need: an incorrectly-formatted email simply won't match any real
    user and gets the same generic "Invalid email or password." failure
    (AD-6 §10) format validation would have produced anyway. `password`
    is never logged (§15/§16) and is never echoed back in any response.
    """

    email: str
    password: str


class AuthenticatedUserResponse(BaseModel):
    """
    The one response shape shared by POST /api/v1/auth/login's success
    case and GET /api/v1/auth/me -- a direct serialization of
    `AuthenticatedUser` (§7 of the frozen architecture: user_id, email,
    roles). Never carries `password_hash`, the session token, or the
    signing secret.
    """

    userId: str
    email: str
    roles: List[str]
