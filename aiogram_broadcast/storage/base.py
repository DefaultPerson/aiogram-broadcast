"""Abstract base storage for aiogram-broadcast."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from aiogram_broadcast.models import Subscriber, SubscriberState


class BaseBroadcastStorage(ABC):
    """
    Abstract base class for subscriber storage.

    Implementations must provide methods for managing subscribers
    and their states.
    """

    @abstractmethod
    async def add_subscriber(self, subscriber: Subscriber) -> None:
        """
        Add a new subscriber to storage.

        Args:
            subscriber: Subscriber instance to add.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_subscriber(self, user_id: int) -> Subscriber | None:
        """
        Get subscriber by user ID.

        Args:
            user_id: Telegram user ID.

        Returns:
            Subscriber instance or None if not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_subscriber(self, subscriber: Subscriber) -> None:
        """
        Update existing subscriber data.

        Args:
            subscriber: Subscriber instance with updated data.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_subscriber(self, user_id: int) -> bool:
        """
        Delete subscriber from storage.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if subscriber was deleted, False if not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all_subscriber_ids(
        self,
        state: SubscriberState | None = None,
    ) -> list[int]:
        """
        Get list of all subscriber IDs.

        Args:
            state: Optional filter by subscriber state.

        Returns:
            List of user IDs.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_subscribers_count(
        self,
        state: SubscriberState | None = None,
    ) -> int:
        """
        Get total count of subscribers.

        Args:
            state: Optional filter by subscriber state.

        Returns:
            Number of subscribers.
        """
        raise NotImplementedError

    @abstractmethod
    async def iter_subscribers(
        self,
        state: SubscriberState | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[Subscriber]:
        """
        Iterate over subscribers in batches.

        Args:
            state: Optional filter by subscriber state.
            batch_size: Number of subscribers to fetch at once.

        Yields:
            Subscriber instances.
        """
        raise NotImplementedError
        yield  # Make this a generator

    async def get_or_create_subscriber(
        self,
        user_id: int,
        full_name: str,
        username: str | None = None,
        language_code: str | None = None,
    ) -> tuple[Subscriber, bool]:
        """
        Get existing subscriber or create a new one.

        Args:
            user_id: Telegram user ID.
            full_name: User's full name.
            username: User's username.
            language_code: User's language code.

        Returns:
            Tuple of (Subscriber, created) where created is True if new.
        """
        subscriber = await self.get_subscriber(user_id)
        if subscriber is not None:
            return subscriber, False

        subscriber = Subscriber(
            id=user_id,
            full_name=full_name,
            username=username,
            language_code=language_code,
        )
        await self.add_subscriber(subscriber)
        return subscriber, True

    async def update_subscriber_state(
        self,
        user_id: int,
        state: SubscriberState,
    ) -> bool:
        """
        Update subscriber's state.

        Args:
            user_id: Telegram user ID.
            state: New subscriber state.

        Returns:
            True if updated, False if subscriber not found.
        """
        subscriber = await self.get_subscriber(user_id)
        if subscriber is None:
            return False

        subscriber.state = state
        await self.update_subscriber(subscriber)
        return True

    async def close(self) -> None:
        """
        Close storage connection.

        Override this method if your storage needs cleanup.
        """
        pass
