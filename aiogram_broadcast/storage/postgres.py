"""PostgreSQL storage implementation for aiogram-broadcast."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aiogram_broadcast.models import Subscriber, SubscriberState
from aiogram_broadcast.storage.base import BaseBroadcastStorage

if TYPE_CHECKING:
    from asyncpg import Pool, Record


class PostgresBroadcastStorage(BaseBroadcastStorage):
    """
    PostgreSQL-based storage for subscribers (using asyncpg).

    Each subscriber is stored as a single row with columns:
    ``id``, ``full_name``, ``username``, ``language_code``, ``state``,
    ``subscribed_at``. Filtering and counting by state are backed by an index,
    so they stay fast on large subscriber bases.

    The table name is configurable (default: ``broadcast_subscribers``).
    Call :meth:`create_schema` once on startup to create the table and index.
    """

    def __init__(
        self,
        pool: Pool,
        table_name: str = "broadcast_subscribers",
    ) -> None:
        """
        Initialize PostgreSQL storage.

        Args:
            pool: asyncpg connection pool.
            table_name: Name of the subscribers table.
        """
        self._pool = pool
        self._table = table_name

    @classmethod
    async def from_dsn(
        cls,
        dsn: str,
        table_name: str = "broadcast_subscribers",
        **pool_kwargs: Any,
    ) -> PostgresBroadcastStorage:
        """
        Create storage backed by a freshly created connection pool.

        Args:
            dsn: PostgreSQL connection string,
                e.g. ``postgresql://user:pass@host:5432/db``.
            table_name: Name of the subscribers table.
            **pool_kwargs: Extra arguments forwarded to ``asyncpg.create_pool``.

        Returns:
            A ready-to-use storage instance that owns the new pool.
        """
        import asyncpg

        pool = await asyncpg.create_pool(dsn, **pool_kwargs)
        return cls(pool, table_name=table_name)

    @property
    def pool(self) -> Pool:
        """Get the asyncpg connection pool."""
        return self._pool

    async def create_schema(self) -> None:
        """
        Create the subscribers table and index if they do not exist.

        Safe to call multiple times. Call once during application startup.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id BIGINT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    username TEXT,
                    language_code TEXT,
                    state TEXT NOT NULL DEFAULT 'member',
                    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            await conn.execute(
                f"CREATE INDEX IF NOT EXISTS {self._table}_state_idx ON {self._table} (state)"
            )

    async def add_subscriber(self, subscriber: Subscriber) -> None:
        """Insert a subscriber, replacing any existing row with the same id."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self._table}
                    (id, full_name, username, language_code, state, subscribed_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    username = EXCLUDED.username,
                    language_code = EXCLUDED.language_code,
                    state = EXCLUDED.state,
                    subscribed_at = EXCLUDED.subscribed_at
                """,
                subscriber.id,
                subscriber.full_name,
                subscriber.username,
                subscriber.language_code,
                subscriber.state.value,
                datetime.fromisoformat(subscriber.subscribed_at),
            )

    async def get_subscriber(self, user_id: int) -> Subscriber | None:
        """Get a subscriber by user ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT id, full_name, username, language_code, state, subscribed_at "
                f"FROM {self._table} WHERE id = $1",
                user_id,
            )
        if row is None:
            return None
        return self._row_to_subscriber(row)

    async def update_subscriber(self, subscriber: Subscriber) -> None:
        """Update an existing subscriber (upsert, identical to add)."""
        await self.add_subscriber(subscriber)

    async def delete_subscriber(self, user_id: int) -> bool:
        """Delete a subscriber. Returns True if a row was removed."""
        async with self._pool.acquire() as conn:
            deleted = await conn.fetchval(
                f"DELETE FROM {self._table} WHERE id = $1 RETURNING id",
                user_id,
            )
        return deleted is not None

    async def get_all_subscriber_ids(
        self,
        state: SubscriberState | None = None,
    ) -> list[int]:
        """Get all subscriber IDs, optionally filtered by state."""
        async with self._pool.acquire() as conn:
            if state is None:
                rows = await conn.fetch(f"SELECT id FROM {self._table} ORDER BY id")
            else:
                rows = await conn.fetch(
                    f"SELECT id FROM {self._table} WHERE state = $1 ORDER BY id",
                    state.value,
                )
        return [int(row["id"]) for row in rows]

    async def get_subscribers_count(
        self,
        state: SubscriberState | None = None,
    ) -> int:
        """Get count of subscribers, optionally filtered by state."""
        async with self._pool.acquire() as conn:
            if state is None:
                count = await conn.fetchval(f"SELECT count(*) FROM {self._table}")
            else:
                count = await conn.fetchval(
                    f"SELECT count(*) FROM {self._table} WHERE state = $1",
                    state.value,
                )
        return int(count)

    async def iter_subscribers(
        self,
        state: SubscriberState | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[Subscriber]:
        """
        Iterate over subscribers in batches using keyset pagination on ``id``.

        The connection is released back to the pool between batches, so it is
        never held while the caller processes (e.g. sends) each subscriber.
        Telegram user IDs are positive, so iteration starts from ``id > 0``.
        """
        last_id = 0
        columns = "id, full_name, username, language_code, state, subscribed_at"
        while True:
            async with self._pool.acquire() as conn:
                if state is None:
                    rows = await conn.fetch(
                        f"SELECT {columns} FROM {self._table} WHERE id > $1 ORDER BY id LIMIT $2",
                        last_id,
                        batch_size,
                    )
                else:
                    rows = await conn.fetch(
                        f"SELECT {columns} FROM {self._table} "
                        f"WHERE id > $1 AND state = $2 ORDER BY id LIMIT $3",
                        last_id,
                        state.value,
                        batch_size,
                    )

            if not rows:
                break

            for row in rows:
                yield self._row_to_subscriber(row)

            last_id = int(rows[-1]["id"])

            if len(rows) < batch_size:
                break

    async def get_active_subscriber_ids(self) -> list[int]:
        """
        Get IDs of active subscribers (state=member).

        Convenience method for the common case of broadcasting only to
        active subscribers.
        """
        return await self.get_all_subscriber_ids(state=SubscriberState.MEMBER)

    async def mark_as_blocked(self, user_id: int) -> bool:
        """
        Mark a subscriber as blocked (kicked).

        Convenience method for handling blocked users during broadcast.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if updated, False if subscriber not found.
        """
        return await self.update_subscriber_state(user_id, SubscriberState.KICKED)

    async def close(self) -> None:
        """Close the connection pool."""
        await self._pool.close()

    @staticmethod
    def _row_to_subscriber(row: Record) -> Subscriber:
        """Build a Subscriber from a database row."""
        return Subscriber(
            id=int(row["id"]),
            full_name=row["full_name"],
            username=row["username"],
            language_code=row["language_code"],
            state=SubscriberState(row["state"]),
            subscribed_at=row["subscribed_at"].isoformat(),
        )
