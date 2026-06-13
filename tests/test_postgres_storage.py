"""Integration tests for PostgresBroadcastStorage.

These tests require a real PostgreSQL instance and run only when the
``DATABASE_URL`` environment variable is set (e.g. in CI with a postgres
service). They are skipped otherwise.

Run locally with a throwaway database, for example:

    docker run -d --rm -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=test \\
        -p 5432:5432 postgres:16
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test pytest -v
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import datetime

import pytest
import pytest_asyncio

from aiogram_broadcast.models import Subscriber, SubscriberState
from aiogram_broadcast.storage.postgres import PostgresBroadcastStorage

DATABASE_URL = os.getenv("DATABASE_URL")
TABLE = "test_broadcast_subscribers"

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set; PostgreSQL integration tests skipped",
)


@pytest_asyncio.fixture
async def pg_storage() -> AsyncIterator[PostgresBroadcastStorage]:
    import asyncpg

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    storage = PostgresBroadcastStorage(pool, table_name=TABLE)
    await storage.create_schema()
    async with pool.acquire() as conn:
        await conn.execute(f"TRUNCATE {TABLE}")
    try:
        yield storage
    finally:
        async with pool.acquire() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
        await pool.close()


class TestPostgresStorage:
    async def test_add_and_get_roundtrip(self, pg_storage: PostgresBroadcastStorage) -> None:
        sub = Subscriber(
            id=1,
            full_name="Alice",
            username="alice",
            language_code="en",
            subscribed_at="2024-03-11T15:30:00+00:00",
        )
        await pg_storage.add_subscriber(sub)

        result = await pg_storage.get_subscriber(1)
        assert result is not None
        assert result.id == 1
        assert result.full_name == "Alice"
        assert result.username == "alice"
        assert result.language_code == "en"
        assert result.state == SubscriberState.MEMBER
        assert datetime.fromisoformat(result.subscribed_at) == datetime.fromisoformat(
            sub.subscribed_at
        )

    async def test_get_not_found(self, pg_storage: PostgresBroadcastStorage) -> None:
        assert await pg_storage.get_subscriber(999) is None

    async def test_nullable_fields(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(Subscriber(id=2, full_name="Bob"))
        result = await pg_storage.get_subscriber(2)
        assert result is not None
        assert result.username is None
        assert result.language_code is None

    async def test_update_subscriber(self, pg_storage: PostgresBroadcastStorage) -> None:
        sub = Subscriber(id=3, full_name="Old Name")
        await pg_storage.add_subscriber(sub)

        sub.full_name = "New Name"
        sub.state = SubscriberState.KICKED
        await pg_storage.update_subscriber(sub)

        result = await pg_storage.get_subscriber(3)
        assert result is not None
        assert result.full_name == "New Name"
        assert result.state == SubscriberState.KICKED

    async def test_add_is_upsert(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(Subscriber(id=4, full_name="First"))
        await pg_storage.add_subscriber(Subscriber(id=4, full_name="Second"))
        result = await pg_storage.get_subscriber(4)
        assert result is not None
        assert result.full_name == "Second"
        assert await pg_storage.get_subscribers_count() == 1

    async def test_delete_found(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(Subscriber(id=5, full_name="X"))
        assert await pg_storage.delete_subscriber(5) is True
        assert await pg_storage.get_subscriber(5) is None

    async def test_delete_not_found(self, pg_storage: PostgresBroadcastStorage) -> None:
        assert await pg_storage.delete_subscriber(999) is False

    async def test_get_all_ids_no_filter(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(Subscriber(id=3, full_name="C"))
        await pg_storage.add_subscriber(Subscriber(id=1, full_name="A"))
        await pg_storage.add_subscriber(Subscriber(id=2, full_name="B"))
        assert await pg_storage.get_all_subscriber_ids() == [1, 2, 3]

    async def test_get_all_ids_filtered(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(
            Subscriber(id=1, full_name="A", state=SubscriberState.MEMBER)
        )
        await pg_storage.add_subscriber(
            Subscriber(id=2, full_name="B", state=SubscriberState.KICKED)
        )
        await pg_storage.add_subscriber(
            Subscriber(id=3, full_name="C", state=SubscriberState.MEMBER)
        )
        assert await pg_storage.get_all_subscriber_ids(SubscriberState.MEMBER) == [1, 3]
        assert await pg_storage.get_all_subscriber_ids(SubscriberState.KICKED) == [2]

    async def test_count(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(
            Subscriber(id=1, full_name="A", state=SubscriberState.MEMBER)
        )
        await pg_storage.add_subscriber(
            Subscriber(id=2, full_name="B", state=SubscriberState.KICKED)
        )
        assert await pg_storage.get_subscribers_count() == 2
        assert await pg_storage.get_subscribers_count(SubscriberState.MEMBER) == 1
        assert await pg_storage.get_subscribers_count(SubscriberState.KICKED) == 1

    async def test_iter_subscribers_multi_batch(self, pg_storage: PostgresBroadcastStorage) -> None:
        for i in range(1, 6):
            await pg_storage.add_subscriber(Subscriber(id=i, full_name=f"U{i}"))
        results = [s async for s in pg_storage.iter_subscribers(batch_size=2)]
        assert [s.id for s in results] == [1, 2, 3, 4, 5]

    async def test_iter_subscribers_filtered(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(
            Subscriber(id=1, full_name="A", state=SubscriberState.MEMBER)
        )
        await pg_storage.add_subscriber(
            Subscriber(id=2, full_name="B", state=SubscriberState.KICKED)
        )
        await pg_storage.add_subscriber(
            Subscriber(id=3, full_name="C", state=SubscriberState.MEMBER)
        )
        results = [
            s async for s in pg_storage.iter_subscribers(state=SubscriberState.MEMBER, batch_size=1)
        ]
        assert [s.id for s in results] == [1, 3]

    async def test_iter_subscribers_empty(self, pg_storage: PostgresBroadcastStorage) -> None:
        results = [s async for s in pg_storage.iter_subscribers()]
        assert results == []

    async def test_update_subscriber_state(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(Subscriber(id=1, full_name="A"))
        assert await pg_storage.update_subscriber_state(1, SubscriberState.KICKED) is True
        result = await pg_storage.get_subscriber(1)
        assert result is not None
        assert result.state == SubscriberState.KICKED

    async def test_update_state_not_found(self, pg_storage: PostgresBroadcastStorage) -> None:
        assert await pg_storage.update_subscriber_state(999, SubscriberState.KICKED) is False

    async def test_get_or_create(self, pg_storage: PostgresBroadcastStorage) -> None:
        sub, created = await pg_storage.get_or_create_subscriber(7, "New User")
        assert created is True
        assert sub.id == 7
        sub2, created2 = await pg_storage.get_or_create_subscriber(7, "Ignored")
        assert created2 is False
        assert sub2.full_name == "New User"

    async def test_get_active_subscriber_ids(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(
            Subscriber(id=1, full_name="A", state=SubscriberState.MEMBER)
        )
        await pg_storage.add_subscriber(
            Subscriber(id=2, full_name="B", state=SubscriberState.KICKED)
        )
        assert await pg_storage.get_active_subscriber_ids() == [1]

    async def test_mark_as_blocked(self, pg_storage: PostgresBroadcastStorage) -> None:
        await pg_storage.add_subscriber(Subscriber(id=1, full_name="A"))
        assert await pg_storage.mark_as_blocked(1) is True
        result = await pg_storage.get_subscriber(1)
        assert result is not None
        assert result.state == SubscriberState.KICKED


async def test_from_dsn() -> None:
    assert DATABASE_URL is not None
    storage = await PostgresBroadcastStorage.from_dsn(
        DATABASE_URL, table_name="test_from_dsn_subscribers", min_size=1, max_size=2
    )
    try:
        await storage.create_schema()
        await storage.add_subscriber(Subscriber(id=1, full_name="A"))
        result = await storage.get_subscriber(1)
        assert result is not None
        assert result.full_name == "A"
    finally:
        async with storage.pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS test_from_dsn_subscribers")
        await storage.close()
