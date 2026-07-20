from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database.session import get_db_session
from backend.services.anomaly_service.app.repositories.anomaly_repository import AnomalyRepository
from backend.services.anomaly_service.app.repositories.trend_repository import TrendRepository
from backend.services.anomaly_service.app.services.anomaly_engine import AnomalyEngine
from backend.services.anomaly_service.app.services.trend_engine import TrendEngine


def get_trend_repository(
    session: AsyncSession = Depends(get_db_session)
) -> TrendRepository:
    """Provides a configured TrendRepository instance."""
    return TrendRepository(session)


def get_trend_engine(
    repository: TrendRepository = Depends(get_trend_repository)
) -> TrendEngine:
    """Provides a configured TrendEngine instance."""
    return TrendEngine(repository)


def get_anomaly_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AnomalyRepository:
    """Provides a configured AnomalyRepository instance."""
    return AnomalyRepository(session)


def get_anomaly_engine(
    repository: AnomalyRepository = Depends(get_anomaly_repository),
    trend_repository: TrendRepository = Depends(get_trend_repository),
) -> AnomalyEngine:
    """Provides a configured AnomalyEngine instance."""
    return AnomalyEngine(repository, trend_repository)
