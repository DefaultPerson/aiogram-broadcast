"""Broadcast service for sending messages to subscribers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import (
    ForceReply,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from aiogram_broadcast.exceptions import BroadcastInProgressError
from aiogram_broadcast.models import BroadcastResult, SubscriberState
from aiogram_broadcast.storage.base import BaseBroadcastStorage

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

ReplyMarkup = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply | None
ProgressCallback = Callable[[int, int, BroadcastResult], Awaitable[None]]


class BroadcastService:
    """
    Service for broadcasting messages to subscribers.

    Features:
    - Rate limiting to avoid hitting Telegram API limits
    - Automatic handling of blocked users
    - Progress callbacks for monitoring
    - Support for text, photo, video, document, and copy broadcasts

    Usage:
        service = BroadcastService(bot, storage)
        result = await service.broadcast_text("Hello everyone!")
    """

    def __init__(
        self,
        bot: Bot,
        storage: BaseBroadcastStorage,
        rate_limit: float = 0.05,  # 20 messages per second
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize broadcast service.

        Args:
            bot: Aiogram Bot instance.
            storage: Broadcast storage instance.
            rate_limit: Minimum delay between messages in seconds.
                        Default 0.05 = 20 msg/sec (Telegram limit is ~30/sec).
            max_retries: Maximum retries for transient errors.
            retry_delay: Delay between retries in seconds.
        """
        self._bot = bot
        self._storage = storage
        self._rate_limit = rate_limit
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._in_progress = False

    @property
    def bot(self) -> Bot:
        """Get bot instance."""
        return self._bot

    @property
    def storage(self) -> BaseBroadcastStorage:
        """Get storage instance."""
        return self._storage

    @property
    def is_broadcasting(self) -> bool:
        """Check if broadcast is currently in progress."""
        return self._in_progress

    async def broadcast_text(
        self,
        text: str,
        parse_mode: str | None = None,
        link_preview_options: LinkPreviewOptions | None = None,
        reply_markup: ReplyMarkup = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        only_active: bool = True,
        progress_callback: ProgressCallback | None = None,
        **kwargs: Any,
    ) -> BroadcastResult:
        """
        Broadcast text message to all subscribers.

        Args:
            text: Message text.
            parse_mode: Parse mode (HTML, Markdown, etc.).
            link_preview_options: Link preview options.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            protect_content: Protect content from forwarding.
            only_active: Only send to active subscribers (state=member).
            progress_callback: Async callback for progress updates.
            **kwargs: Additional arguments for send_message.

        Returns:
            BroadcastResult with statistics.
        """
        async def sender(chat_id: int) -> None:
            await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                link_preview_options=link_preview_options,
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                protect_content=protect_content,
                **kwargs,
            )

        return await self._broadcast(
            sender=sender,
            only_active=only_active,
            progress_callback=progress_callback,
        )

    async def broadcast_photo(
        self,
        photo: str,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: ReplyMarkup = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        only_active: bool = True,
        progress_callback: ProgressCallback | None = None,
        **kwargs: Any,
    ) -> BroadcastResult:
        """
        Broadcast photo to all subscribers.

        Args:
            photo: Photo file_id or URL.
            caption: Photo caption.
            parse_mode: Parse mode for caption.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            protect_content: Protect content from forwarding.
            only_active: Only send to active subscribers.
            progress_callback: Async callback for progress updates.
            **kwargs: Additional arguments for send_photo.

        Returns:
            BroadcastResult with statistics.
        """
        async def sender(chat_id: int) -> None:
            await self._bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                protect_content=protect_content,
                **kwargs,
            )

        return await self._broadcast(
            sender=sender,
            only_active=only_active,
            progress_callback=progress_callback,
        )

    async def broadcast_video(
        self,
        video: str,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: ReplyMarkup = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        only_active: bool = True,
        progress_callback: ProgressCallback | None = None,
        **kwargs: Any,
    ) -> BroadcastResult:
        """
        Broadcast video to all subscribers.

        Args:
            video: Video file_id or URL.
            caption: Video caption.
            parse_mode: Parse mode for caption.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            protect_content: Protect content from forwarding.
            only_active: Only send to active subscribers.
            progress_callback: Async callback for progress updates.
            **kwargs: Additional arguments for send_video.

        Returns:
            BroadcastResult with statistics.
        """
        async def sender(chat_id: int) -> None:
            await self._bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                protect_content=protect_content,
                **kwargs,
            )

        return await self._broadcast(
            sender=sender,
            only_active=only_active,
            progress_callback=progress_callback,
        )

    async def broadcast_document(
        self,
        document: str,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: ReplyMarkup = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        only_active: bool = True,
        progress_callback: ProgressCallback | None = None,
        **kwargs: Any,
    ) -> BroadcastResult:
        """
        Broadcast document to all subscribers.

        Args:
            document: Document file_id or URL.
            caption: Document caption.
            parse_mode: Parse mode for caption.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            protect_content: Protect content from forwarding.
            only_active: Only send to active subscribers.
            progress_callback: Async callback for progress updates.
            **kwargs: Additional arguments for send_document.

        Returns:
            BroadcastResult with statistics.
        """
        async def sender(chat_id: int) -> None:
            await self._bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                protect_content=protect_content,
                **kwargs,
            )

        return await self._broadcast(
            sender=sender,
            only_active=only_active,
            progress_callback=progress_callback,
        )

    async def broadcast_copy(
        self,
        from_chat_id: int,
        message_id: int,
        caption: str | None = None,
        parse_mode: str | None = None,
        reply_markup: ReplyMarkup = None,
        disable_notification: bool = False,
        protect_content: bool = False,
        only_active: bool = True,
        progress_callback: ProgressCallback | None = None,
        **kwargs: Any,
    ) -> BroadcastResult:
        """
        Copy and broadcast a message to all subscribers.

        This is useful for forwarding admin messages to all users.

        Args:
            from_chat_id: Source chat ID.
            message_id: Source message ID.
            caption: New caption (if applicable).
            parse_mode: Parse mode for caption.
            reply_markup: Reply markup.
            disable_notification: Disable notification.
            protect_content: Protect content from forwarding.
            only_active: Only send to active subscribers.
            progress_callback: Async callback for progress updates.
            **kwargs: Additional arguments for copy_message.

        Returns:
            BroadcastResult with statistics.
        """
        async def sender(chat_id: int) -> None:
            await self._bot.copy_message(
                chat_id=chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_notification=disable_notification,
                protect_content=protect_content,
                **kwargs,
            )

        return await self._broadcast(
            sender=sender,
            only_active=only_active,
            progress_callback=progress_callback,
        )

    async def broadcast_custom(
        self,
        sender: Callable[[int], Awaitable[None]],
        only_active: bool = True,
        progress_callback: ProgressCallback | None = None,
    ) -> BroadcastResult:
        """
        Broadcast using a custom sender function.

        Use this for complex broadcasts that don't fit other methods.

        Args:
            sender: Async function that takes chat_id and sends message.
            only_active: Only send to active subscribers.
            progress_callback: Async callback for progress updates.

        Returns:
            BroadcastResult with statistics.

        Example:
            async def send_sticker(chat_id: int):
                await bot.send_sticker(chat_id, sticker_file_id)

            result = await service.broadcast_custom(send_sticker)
        """
        return await self._broadcast(
            sender=sender,
            only_active=only_active,
            progress_callback=progress_callback,
        )

    async def _broadcast(
        self,
        sender: Callable[[int], Awaitable[None]],
        only_active: bool = True,
        progress_callback: ProgressCallback | None = None,
    ) -> BroadcastResult:
        """
        Internal broadcast implementation.

        Args:
            sender: Async function that sends message to chat_id.
            only_active: Only send to active subscribers.
            progress_callback: Progress callback.

        Returns:
            BroadcastResult with statistics.
        """
        if self._in_progress:
            raise BroadcastInProgressError("Another broadcast is already in progress")

        self._in_progress = True
        result = BroadcastResult()

        try:
            # Get subscriber IDs
            state_filter = SubscriberState.MEMBER if only_active else None
            subscriber_ids = await self._storage.get_all_subscriber_ids(state=state_filter)
            result.total = len(subscriber_ids)

            logger.info(f"Starting broadcast to {result.total} subscribers")

            for i, user_id in enumerate(subscriber_ids, 1):
                success = await self._send_with_retry(sender, user_id, result)

                # Update progress
                if progress_callback and i % 10 == 0:
                    try:
                        await progress_callback(i, result.total, result)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

                # Rate limiting
                if success and self._rate_limit > 0:
                    await asyncio.sleep(self._rate_limit)

            logger.info(
                f"Broadcast completed: {result.successful}/{result.total} successful, "
                f"{result.failed} failed, {len(result.blocked_users)} blocked"
            )

            return result

        finally:
            self._in_progress = False

    async def _send_with_retry(
        self,
        sender: Callable[[int], Awaitable[None]],
        user_id: int,
        result: BroadcastResult,
    ) -> bool:
        """
        Send message with retry logic.

        Returns:
            True if message was sent successfully.
        """
        for attempt in range(self._max_retries):
            try:
                await sender(user_id)
                result.add_success()
                return True

            except TelegramForbiddenError as e:
                # User blocked the bot
                error_msg = str(e)
                is_blocked = "blocked" in error_msg.lower() or "kicked" in error_msg.lower()
                result.add_failure(user_id, error_msg, is_blocked=is_blocked)

                if is_blocked:
                    # Update subscriber state
                    await self._storage.update_subscriber_state(
                        user_id, SubscriberState.KICKED
                    )

                return False

            except TelegramRetryAfter as e:
                # Rate limit hit - wait and retry
                wait_time = e.retry_after
                logger.warning(f"Rate limit hit, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                continue

            except TelegramAPIError as e:
                # Other API errors
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                    continue

                result.add_failure(user_id, str(e))
                logger.warning(f"Failed to send to {user_id}: {e}")
                return False

            except Exception as e:
                # Unexpected errors
                result.add_failure(user_id, str(e))
                logger.error(f"Unexpected error sending to {user_id}: {e}")
                return False

        return False

    async def get_subscriber_count(self, only_active: bool = True) -> int:
        """
        Get count of subscribers.

        Args:
            only_active: Only count active subscribers.

        Returns:
            Number of subscribers.
        """
        state_filter = SubscriberState.MEMBER if only_active else None
        return await self._storage.get_subscribers_count(state=state_filter)
