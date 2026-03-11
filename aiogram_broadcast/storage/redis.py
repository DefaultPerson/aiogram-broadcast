"""Redis storage implementation for aiogram-broadcast."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from aiogram_broadcast.models import Subscriber, SubscriberState
from aiogram_broadcast.storage.base import BaseBroadcastStorage

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisBroadcastStorage(BaseBroadcastStorage):
    """
    Redis-based storage for subscribers.

    Stores subscribers in a Redis hash where:
    - Key: configurable hash name (default: "broadcast:subscribers")
    - Field: user_id
    - Value: JSON-encoded Subscriber data
    """

    def __init__(
        self,
        redis: Redis,
        key_prefix: str = "broadcast",
    ) -> None:
        """
        Initialize Redis storage.

        Args:
            redis: Redis async client instance.
            key_prefix: Prefix for Redis keys.
        """
        self._redis = redis
        self._key_prefix = key_prefix
        self._subscribers_key = f"{key_prefix}:subscribers"

    @property
    def redis(self) -> Redis:
        """Get Redis client."""
        return self._redis

    async def add_subscriber(self, subscriber: Subscriber) -> None:
        """Add a new subscriber to Redis hash."""
        data = json.dumps(subscriber.to_dict())
        await self._redis.hset(self._subscribers_key, str(subscriber.id), data)  # type: ignore[misc]

    async def get_subscriber(self, user_id: int) -> Subscriber | None:
        """Get subscriber from Redis hash."""
        data = await self._redis.hget(self._subscribers_key, str(user_id))  # type: ignore[misc]
        if data is None:
            return None
        return Subscriber.from_dict(json.loads(data))

    async def update_subscriber(self, subscriber: Subscriber) -> None:
        """Update subscriber in Redis hash."""
        await self.add_subscriber(subscriber)

    async def delete_subscriber(self, user_id: int) -> bool:
        """Delete subscriber from Redis hash."""
        deleted: int = await self._redis.hdel(self._subscribers_key, str(user_id))  # type: ignore[misc]
        return deleted > 0

    async def get_all_subscriber_ids(
        self,
        state: SubscriberState | None = None,
    ) -> list[int]:
        """Get all subscriber IDs, optionally filtered by state."""
        if state is None:
            # Fast path: just get all keys
            keys: list[Any] = await self._redis.hkeys(self._subscribers_key)  # type: ignore[misc]
            return [int(k) for k in keys]

        # Slow path: need to filter by state
        result = []
        async for subscriber in self.iter_subscribers(state=state):
            result.append(subscriber.id)
        return result

    async def get_subscribers_count(
        self,
        state: SubscriberState | None = None,
    ) -> int:
        """Get count of subscribers, optionally filtered by state."""
        if state is None:
            result: int = await self._redis.hlen(self._subscribers_key)  # type: ignore[misc]
            return result

        # Need to count filtered subscribers
        count = 0
        async for _ in self.iter_subscribers(state=state):
            count += 1
        return count

    async def iter_subscribers(
        self,
        state: SubscriberState | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[Subscriber]:
        """Iterate over subscribers using HSCAN."""
        cursor = 0
        while True:
            cursor, data = await self._redis.hscan(
                self._subscribers_key,
                cursor=cursor,
                count=batch_size,
            )

            for _, value in data.items():
                subscriber = Subscriber.from_dict(json.loads(value))
                if state is None or subscriber.state == state:
                    yield subscriber

            if cursor == 0:
                break

    async def get_active_subscriber_ids(self) -> list[int]:
        """
        Get IDs of active subscribers (state=member).

        This is a convenience method for the common use case
        of getting only active subscribers for broadcast.
        """
        return await self.get_all_subscriber_ids(state=SubscriberState.MEMBER)

    async def mark_as_blocked(self, user_id: int) -> bool:
        """
        Mark subscriber as blocked (kicked).

        Convenience method for handling blocked users during broadcast.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if updated, False if subscriber not found.
        """
        return await self.update_subscriber_state(user_id, SubscriberState.KICKED)

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.aclose()
