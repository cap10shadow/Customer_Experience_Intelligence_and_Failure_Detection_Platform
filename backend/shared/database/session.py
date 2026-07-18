from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database.database import async_session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Typed shorthand for FastAPI dependency injection in route signatures and repositories.
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
