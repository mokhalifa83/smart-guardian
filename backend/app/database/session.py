from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from app.core.config import settings
from app.core.logging import logger

Base = declarative_base()


def get_engine():
    engine_kwargs = {"echo": False}
    if "sqlite" in settings.DATABASE_URL:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(settings.DATABASE_URL, **engine_kwargs)


async_engine = get_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session exception: {e}", exc_info=True)
            raise
        finally:
            await session.close()
