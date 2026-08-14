from typing import Annotated

from fastapi import Depends

from backend.services.gateway_service.app.repositories.identity_repository import RoleRepository, UserRepository
from backend.shared.database.session import DbSession

"""
Phase 13 Batch 1 (AD-1): dependency-injection providers for the new
identity repositories, matching ingestion_service's existing
`get_complaint_repository` pattern exactly. Not wired into any route in
this batch -- these providers exist so Batch 3 (Authentication API) can
depend on `UserRepo`/`RoleRepo` without re-deriving this wiring.
"""


def get_user_repository(session: DbSession) -> UserRepository:
    return UserRepository(session)


def get_role_repository(session: DbSession) -> RoleRepository:
    return RoleRepository(session)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
RoleRepo = Annotated[RoleRepository, Depends(get_role_repository)]
