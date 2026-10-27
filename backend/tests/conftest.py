import os
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from pathlib import Path

TEST_DB_FILE = Path("test_sg.db")
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.resolve()}"

# Set environment before any app import
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE.resolve()}"

from app.core.config import settings
settings.ENVIRONMENT = "test"
settings.DATABASE_URL = TEST_DB_URL
settings.SYNC_DATABASE_URL = f"sqlite:///{TEST_DB_FILE.resolve()}"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.session import Base, get_db
from app.main import app
from httpx import AsyncClient, ASGITransport

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False}
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
