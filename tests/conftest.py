"""Test fixtures.

The suite runs against in-memory SQLite so `pytest` works with no infrastructure at
all. Postgres-specific behaviour is covered by the integration job in CI, which points
APP_DATABASE_URL at a real database and runs the same tests.
"""

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db import Base
from app.deps import get_session
from app.main import create_app
from app.models import Item  # noqa: F401  - registers the table on Base.metadata

API_KEY = "test-key"

# Defaults to in-memory SQLite so `pytest` needs no infrastructure. CI's integration
# job points this at a real Postgres and runs the identical suite.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        env="ci",
        api_keys=[API_KEY],
        database_url=TEST_DATABASE_URL,
        redis_url="",
        log_level="WARNING",
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)

    # One engine and one connection for the whole test: in-memory SQLite discards
    # the database when the last connection closes.
    # In-memory SQLite drops the database when its last connection closes, so the
    # whole test has to share one. A real Postgres wants a normal pool.
    if settings.database_url.startswith("sqlite"):
        engine = create_async_engine(
            settings.database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[object]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_session

    # httpx's ASGITransport does not run startup/shutdown, so enter the app's
    # lifespan by hand - otherwise app.state.db and app.state.cache never exist.
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac

    await engine.dispose()


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}
