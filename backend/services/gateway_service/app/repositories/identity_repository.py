import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.gateway_service.app.models.identity import Role, User, UserRole

"""
Identity lookup primitives (Phase 13 Batch 1, AD-1 §7/§8). Persistence
only, matching this platform's existing repository convention
(ComplaintRepository is the closest precedent for a plain,
non-port/adapter repository class): no password verification, no JWT,
no route wiring. Callers (a future Batch 3 login flow, Batch 4 role
assignment, or a test) construct these directly against an
`AsyncSession` -- nothing here is exposed through any Gateway route in
this batch.
"""


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, email: str, password_hash: str) -> User:
        """Persists a new user. Uniqueness of `email` is enforced by the database (uq_users_email)."""
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class RoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, name: str, description: Optional[str] = None) -> Role:
        """Persists a new role. Uniqueness of `name` is enforced by the database (uq_roles_name)."""
        role = Role(name=name, description=description)
        self.session.add(role)
        await self.session.flush()
        return role

    async def get_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        stmt = select(Role).where(Role.id == role_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def assign_to_user(self, *, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole:
        """
        Assigns a role to a user. Uniqueness of the (user_id, role_id)
        pair is enforced by `user_roles`'s own composite primary key --
        a duplicate assignment raises an IntegrityError at flush, not a
        silent no-op.
        """
        assignment = UserRole(user_id=user_id, role_id=role_id)
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def list_for_user(self, user_id: uuid.UUID) -> list[Role]:
        stmt = select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
