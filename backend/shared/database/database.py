from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.shared.config.settings import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)
