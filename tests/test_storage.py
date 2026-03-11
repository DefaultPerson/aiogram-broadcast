"""Tests for storage (base + redis)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest

from aiogram_broadcast.models import Subscriber, SubscriberState
from aiogram_broadcast.storage.base import BaseBroadcastStorage
from aiogram_broadcast.storage.redis import RedisBroadcastStorage

# --- In-memory implementation for testing base class template methods ---


class InMemoryStorage(BaseBroadcastStorage):
    def __init__(self) -> None:
        self._data: dict[int, Subscriber] = {}

    async def add_subscriber(self, subscriber: Subscriber) -> None:
        self._data[subscriber.id] = subscriber

    async def get_subscriber(self, user_id: int) -> Subscriber | None:
        return self._data.get(user_id)

    async def update_subscriber(self, subscriber: Subscriber) -> None:
        self._data[subscriber.id] = subscriber

    async def delete_subscriber(self, user_id: int) -> bool:
        return self._data.pop(user_id, None) is not None

    async def get_all_subscriber_ids(self, state: SubscriberState | None = None) -> list[int]:
        return [s.id for s in self._data.values() if state is None or s.state == state]

    async def get_subscribers_count(self, state: SubscriberState | None = None) -> int:
        return len(await self.get_all_subscriber_ids(state))

    async def iter_subscribers(
        self, state: SubscriberState | None = None, batch_size: int = 100
    ) -> AsyncIterator[Subscriber]:
        for s in self._data.values():
            if state is None or s.state == state:
                yield s


# --- Base storage template methods ---


class TestBaseStorage:
    async def test_get_or_create_existing(self, subscriber: Subscriber) -> None:
        store = InMemoryStorage()
        store._data[subscriber.id] = subscriber
        result, created = await store.get_or_create_subscriber(subscriber.id, "New Name")
        assert created is False
        assert result.id == subscriber.id

    async def test_get_or_create_new(self) -> None:
        store = InMemoryStorage()
        result, created = await store.get_or_create_subscriber(999, "New User")
        assert created is True
        assert result.id == 999
        assert result.full_name == "New User"

    async def test_update_state_found(self, subscriber: Subscriber) -> None:
        store = InMemoryStorage()
        store._data[subscriber.id] = subscriber
        ok = await store.update_subscriber_state(subscriber.id, SubscriberState.KICKED)
        assert ok is True
        assert store._data[subscriber.id].state == SubscriberState.KICKED

    async def test_update_state_not_found(self) -> None:
        store = InMemoryStorage()
        ok = await store.update_subscriber_state(999, SubscriberState.KICKED)
        assert ok is False


# --- Redis storage ---


class TestRedisStorage:
    @pytest.fixture
    def redis_storage(self, mock_redis: AsyncMock) -> RedisBroadcastStorage:
        return RedisBroadcastStorage(mock_redis)

    async def test_add_and_get_roundtrip(
        self, redis_storage: RedisBroadcastStorage, mock_redis: AsyncMock
    ) -> None:
        sub = Subscriber(id=1, full_name="Alice")
        await redis_storage.add_subscriber(sub)
        mock_redis.hset.assert_called_once()

        # Simulate get returning what was stored
        mock_redis.hget.return_value = json.dumps(sub.to_dict())
        result = await redis_storage.get_subscriber(1)
        assert result is not None
        assert result.id == 1
        assert result.full_name == "Alice"

    async def test_get_subscriber_not_found(
        self, redis_storage: RedisBroadcastStorage, mock_redis: AsyncMock
    ) -> None:
        mock_redis.hget.return_value = None
        assert await redis_storage.get_subscriber(999) is None

    async def test_delete_found(
        self, redis_storage: RedisBroadcastStorage, mock_redis: AsyncMock
    ) -> None:
        mock_redis.hdel.return_value = 1
        assert await redis_storage.delete_subscriber(1) is True

    async def test_delete_not_found(
        self, redis_storage: RedisBroadcastStorage, mock_redis: AsyncMock
    ) -> None:
        mock_redis.hdel.return_value = 0
        assert await redis_storage.delete_subscriber(999) is False

    async def test_get_all_ids_no_filter(
        self, redis_storage: RedisBroadcastStorage, mock_redis: AsyncMock
    ) -> None:
        mock_redis.hkeys.return_value = [b"1", b"2", b"3"]
        ids = await redis_storage.get_all_subscriber_ids()
        assert ids == [1, 2, 3]

    async def test_iter_subscribers_multi_batch(
        self, redis_storage: RedisBroadcastStorage, mock_redis: AsyncMock
    ) -> None:
        sub1 = Subscriber(id=1, full_name="A")
        sub2 = Subscriber(id=2, full_name="B")
        # First call returns cursor=5 (not done), second returns cursor=0 (done)
        mock_redis.hscan.side_effect = [
            (5, {b"1": json.dumps(sub1.to_dict()).encode()}),
            (0, {b"2": json.dumps(sub2.to_dict()).encode()}),
        ]
        results = [s async for s in redis_storage.iter_subscribers()]
        assert len(results) == 2
        assert results[0].id == 1
        assert results[1].id == 2
