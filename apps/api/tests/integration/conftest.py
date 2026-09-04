import os
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.adapters.persistence.db.base import Base


@pytest.fixture
async def postgres_sessions():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    schema = f"looksee_test_{uuid4().hex}"
    administration = create_async_engine(url)
    async with administration.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
        async with administration.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await administration.dispose()


@pytest.fixture
async def valkey():
    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL is required for Valkey integration tests")

    async with Redis.from_url(url) as client:
        yield client
