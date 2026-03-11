"""Middleware for automatic subscriber management."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus
from aiogram.types import Chat, ChatMemberUpdated, TelegramObject, User

from aiogram_broadcast.models import Subscriber, SubscriberState
from aiogram_broadcast.storage.base import BaseBroadcastStorage


class BroadcastMiddleware(BaseMiddleware):
    """
    Middleware for automatic subscriber registration and management.

    This middleware:
    - Automatically registers new users as subscribers
    - Updates subscriber info on each interaction
    - Tracks subscribe/unsubscribe events (my_chat_member updates)

    Injects into handler data:
    - `subscriber`: Subscriber instance (or None for non-private chats)
    - `broadcast_storage`: Storage instance

    Usage:
        storage = RedisBroadcastStorage(redis)
        dp.update.outer_middleware.register(BroadcastMiddleware(storage))
    """

    def __init__(
        self,
        storage: BaseBroadcastStorage,
        storage_key: str = "broadcast_storage",
        subscriber_key: str = "subscriber",
    ) -> None:
        """
        Initialize middleware.

        Args:
            storage: Broadcast storage instance.
            storage_key: Key to inject storage into handler data.
            subscriber_key: Key to inject subscriber into handler data.
        """
        self._storage = storage
        self._storage_key = storage_key
        self._subscriber_key = subscriber_key

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process update and manage subscriber."""
        # Always inject storage
        data[self._storage_key] = self._storage

        # Get chat and user from data
        chat: Chat | None = data.get("event_chat")
        user: User | None = data.get("event_from_user")

        subscriber = None

        # Only process private chats
        if chat is not None and chat.type == "private" and user is not None:
            # Handle my_chat_member updates
            if isinstance(event, ChatMemberUpdated):
                subscriber = await self._handle_chat_member_update(event)
            else:
                # Regular message/callback - get or create subscriber
                subscriber = await self._get_or_update_subscriber(user)

        data[self._subscriber_key] = subscriber
        return await handler(event, data)

    async def _get_or_update_subscriber(self, user: User) -> Subscriber:
        """Get existing subscriber or create new one, update info."""
        existing = await self._storage.get_subscriber(user.id)

        if existing is not None:
            # Update subscriber info if changed
            changed = False
            if existing.full_name != user.full_name:
                existing.full_name = user.full_name
                changed = True
            if existing.username != user.username:
                existing.username = user.username
                changed = True
            if existing.language_code != user.language_code:
                existing.language_code = user.language_code
                changed = True
            # If user was kicked but now interacting - they restarted the bot
            if existing.state == SubscriberState.KICKED:
                existing.state = SubscriberState.MEMBER
                changed = True

            if changed:
                await self._storage.update_subscriber(existing)

            return existing

        # Create new subscriber
        subscriber = Subscriber(
            id=user.id,
            full_name=user.full_name,
            username=user.username,
            language_code=user.language_code,
            state=SubscriberState.MEMBER,
        )
        await self._storage.add_subscriber(subscriber)
        return subscriber

    async def _handle_chat_member_update(
        self,
        update: ChatMemberUpdated,
    ) -> Subscriber | None:
        """Handle my_chat_member update (subscribe/unsubscribe)."""
        user = update.from_user
        new_status = update.new_chat_member.status

        # Determine new state based on chat member status
        if new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR):
            new_state = SubscriberState.MEMBER
        else:  # KICKED, LEFT, etc.
            new_state = SubscriberState.KICKED

        existing = await self._storage.get_subscriber(user.id)

        if existing is not None:
            existing.state = new_state
            existing.full_name = user.full_name
            existing.username = user.username
            existing.language_code = user.language_code
            await self._storage.update_subscriber(existing)
            return existing

        # New subscriber from chat member update
        subscriber = Subscriber(
            id=user.id,
            full_name=user.full_name,
            username=user.username,
            language_code=user.language_code,
            state=new_state,
        )
        await self._storage.add_subscriber(subscriber)
        return subscriber


class BroadcastChatMemberMiddleware(BaseMiddleware):
    """
    Specialized middleware for handling my_chat_member updates only.

    Use this if you want to handle subscription changes separately
    from the main BroadcastMiddleware.

    This is useful when you want more control over when subscribers
    are created/updated.
    """

    def __init__(
        self,
        storage: BaseBroadcastStorage,
        on_subscribe: Callable[[Subscriber], Awaitable[None]] | None = None,
        on_unsubscribe: Callable[[Subscriber], Awaitable[None]] | None = None,
    ) -> None:
        """
        Initialize middleware.

        Args:
            storage: Broadcast storage instance.
            on_subscribe: Optional callback when user subscribes.
            on_unsubscribe: Optional callback when user unsubscribes.
        """
        self._storage = storage
        self._on_subscribe = on_subscribe
        self._on_unsubscribe = on_unsubscribe

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process my_chat_member update."""
        if not isinstance(event, ChatMemberUpdated):
            return await handler(event, data)

        if event.chat.type != "private":
            return await handler(event, data)

        user = event.from_user
        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status

        # Check if this is a subscription change
        was_member = old_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)
        is_member = new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)

        if was_member == is_member:
            # No change in subscription status
            return await handler(event, data)

        # Update or create subscriber
        subscriber = await self._storage.get_subscriber(user.id)

        if subscriber is None:
            subscriber = Subscriber(
                id=user.id,
                full_name=user.full_name,
                username=user.username,
                language_code=user.language_code,
            )

        subscriber.full_name = user.full_name
        subscriber.username = user.username
        subscriber.language_code = user.language_code

        if is_member:
            subscriber.state = SubscriberState.MEMBER
            await self._storage.update_subscriber(subscriber)
            if self._on_subscribe:
                await self._on_subscribe(subscriber)
        else:
            subscriber.state = SubscriberState.KICKED
            await self._storage.update_subscriber(subscriber)
            if self._on_unsubscribe:
                await self._on_unsubscribe(subscriber)

        data["subscriber"] = subscriber
        return await handler(event, data)
