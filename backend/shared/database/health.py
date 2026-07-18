import logging
from sqlalchemy import text
from backend.shared.database.database import engine

logger = logging.getLogger(__name__)

async def check_database_connection() -> bool:
    """
    Verifies database connectivity using the async engine.
    Returns True if connection is successful, False otherwise.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
