import os
import tempfile

# Force an in-memory-ish sqlite DB for tests before app imports.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")
# Disable Redis-backed features (worker/pubsub) in tests.
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("METRICS_ENABLED", "false")
# Write uploaded files to a throwaway temp dir during tests.
os.environ.setdefault(
    "MEDIA_ROOT", os.path.join(tempfile.gettempdir(), "studioos-test-media")
)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.db.base import Base
from app.main import app

# Import models so metadata is populated
from app.models import tenant, user  # noqa: F401


@pytest_asyncio.fixture
async def client():
    # Single shared in-memory engine for the test (StaticPool keeps one connection)
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()
