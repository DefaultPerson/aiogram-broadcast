"""Broadcast UI Manager for handling menu navigation and state."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, User

from aiogram_broadcast.ui.keyboards import BroadcastUIKeyboards
from aiogram_broadcast.ui.states import BroadcastUIState
from aiogram_broadcast.ui.texts import BroadcastUITexts
from aiogram_broadcast.ui.utils import (
    MESSAGE_DELETE_ERRORS,
    MESSAGE_EDIT_ERRORS,
    DataStorage,
    send_message_copy,
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

    from aiogram_broadcast.scheduler import BroadcastScheduler
    from aiogram_broadcast.service import BroadcastService


# Type alias for return callback
ReturnCallback = Callable[..., Awaitable[Any]]


class BroadcastUIManager:
    """
    Manager for broadcast UI menu and navigation.

    Handles:
    - Opening and navigating menu windows
    - Managing FSM state
    - Storing message data for broadcasts
    - Scheduling and executing broadcasts

    Usage:
        In middleware, create manager and inject into handler data:

        manager = BroadcastUIManager(
            bot=bot,
            user=user,
            state=state,
            service=broadcast_service,
            scheduler=broadcast_scheduler,
        )
        data["broadcast_ui"] = manager

        In command handler:

        @router.message(Command("broadcast"))
        async def broadcast_command(
            message: Message,
            broadcast_ui: BroadcastUIManager,
            broadcast_storage: BaseBroadcastStorage,
        ):
            subscriber_ids = await broadcast_storage.get_all_subscriber_ids()
            await broadcast_ui.open_menu(subscriber_ids, my_return_callback)
            await message.delete()
    """

    def __init__(
        self,
        bot: Bot,
        user: User,
        state: FSMContext,
        service: BroadcastService,
        scheduler: BroadcastScheduler | None = None,
        texts: BroadcastUITexts | None = None,
        keyboards: BroadcastUIKeyboards | None = None,
        middleware_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize UI manager.

        Args:
            bot: Bot instance.
            user: Current user.
            state: FSM context.
            service: BroadcastService instance.
            scheduler: Optional BroadcastScheduler for scheduled broadcasts.
            texts: Optional custom texts (auto-created from user language if None).
            keyboards: Optional custom keyboards (auto-created from user language if None).
            middleware_data: Optional middleware data dict for return callback.
        """
        self.bot = bot
        self.user = user
        self.state = state
        self.service = service
        self.scheduler = scheduler

        language_code = user.language_code or "en"
        self.texts = texts or BroadcastUITexts(language_code)
        self.keyboards = keyboards or BroadcastUIKeyboards(language_code)

        self._data_storage = DataStorage(state)
        self._middleware_data = middleware_data or {}

    async def update_language(self, language_code: str) -> None:
        """
        Update UI language.

        Args:
            language_code: New language code.
        """
        self.texts = BroadcastUITexts(language_code)
        self.keyboards = BroadcastUIKeyboards(language_code)
        await self.state.update_data(ui_language_code=language_code)

    # =========================================================================
    # Public Menu Methods
    # =========================================================================

    async def open_menu(
        self,
        subscriber_ids: list[int],
        return_callback: ReturnCallback | None = None,
    ) -> Message:
        """
        Open the broadcast menu.

        This is the main entry point for the broadcast UI.

        Args:
            subscriber_ids: List of subscriber IDs for broadcasting.
            return_callback: Optional async callback to call when user exits menu.

        Returns:
            Sent menu message.
        """
        if return_callback is not None:
            await self._data_storage.set("return_callback", return_callback)
        await self.state.update_data(subscriber_ids=subscriber_ids, page=1)
        return await self.open_broadcasts_list()

    async def return_to_caller(self) -> None:
        """
        Return to the caller by executing the return callback.

        Cleans up UI state and calls the stored return callback.
        """
        return_callback = await self._data_storage.get("return_callback")
        if return_callback:
            await return_callback(**self._middleware_data)
        await self.state.set_state(None)

    # =========================================================================
    # Window Methods
    # =========================================================================

    async def open_broadcasts_list(self) -> Message:
        """Open the broadcasts list window with scheduled broadcasts."""
        state_data = await self.state.get_data()
        page = state_data.get("page", 1)
        page_size = 5

        # Get scheduled broadcasts from scheduler
        items: list[tuple[str, str]] = []
        if self.scheduler and self.scheduler.is_configured:
            jobs = self.scheduler.scheduler.get_jobs()
            items = sorted(
                [
                    (job.trigger.run_date.strftime("%Y-%m-%d %H:%M"), f"job:{job.id}")
                    for job in jobs
                    if hasattr(job.trigger, "run_date")
                ],
                key=lambda x: x[0],
            )

        # Pagination
        page_items = items[(page - 1) * page_size : page * page_size]
        total_pages = max(1, (len(items) + page_size - 1) // page_size)

        # Get subscriber count
        subscriber_count = len(state_data.get("subscriber_ids", []))

        text = self.texts.get("broadcasts_list", total=subscriber_count)
        markup = self.keyboards.broadcasts_list(page_items, page, total_pages)

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.broadcasts_list)
        return message

    async def open_broadcast_view(self) -> Message:
        """Open single broadcast view with preview."""
        state_data = await self.state.get_data()
        job_id = state_data.get("job_id")

        if self.scheduler and self.scheduler.is_configured and job_id:
            job = self.scheduler.scheduler.get_job(job_id)
            if job and hasattr(job, "kwargs"):
                message_data = job.kwargs.get("message_data")
                if message_data:
                    # Send preview
                    await send_message_copy(self.bot, self.user.id, message_data)

        text = self.texts.get("broadcast_view")
        markup = self.keyboards.back_delete()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.broadcast_view)
        return message

    async def open_broadcast_delete(self) -> Message:
        """Open broadcast delete confirmation."""
        text = self.texts.get("broadcast_delete")
        markup = self.keyboards.back_confirm()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.broadcast_delete)
        return message

    async def open_send_message(self) -> Message:
        """Open send message window."""
        text = self.texts.get("send_message")
        markup = self.keyboards.back()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.send_message)
        return message

    async def open_send_buttons(self, error_text: str | None = None) -> Message:
        """
        Open send buttons window.

        Args:
            error_text: Optional error message to show instead of default.
        """
        if error_text:
            text = error_text
        else:
            text = self.texts.get("send_buttons")
        markup = self.keyboards.back_skip()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.send_buttons)
        return message

    async def open_message_preview(self) -> Message:
        """Open message preview window."""
        # Send preview message
        message_data = await self._data_storage.get("message_data")
        if message_data:
            await send_message_copy(self.bot, self.user.id, message_data)

        text = self.texts.get("message_preview")
        markup = self.keyboards.back_next()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.message_preview)
        return message

    async def open_choose_options(self) -> Message:
        """Open send options window (now/later)."""
        text = self.texts.get("choose_options")
        markup = self.keyboards.send_options()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.choose_options)
        return message

    async def open_confirmation_now(self) -> Message:
        """Open immediate send confirmation."""
        text = self.texts.get("confirmation_now")
        markup = self.keyboards.back_confirm()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.confirmation_now)
        return message

    async def open_send_datetime(self, error_text: str | None = None) -> Message:
        """
        Open datetime input window.

        Args:
            error_text: Optional error message to show instead of default.
        """
        datetime_now = datetime.now()
        datetime_string = datetime_now.strftime("%Y-%m-%d %H:%M")

        if error_text:
            text = error_text
        else:
            text = self.texts.get("send_datetime", datetime_string=datetime_string)
        markup = self.keyboards.back()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.send_datetime)
        return message

    async def open_confirmation_later(self) -> Message:
        """Open scheduled send confirmation."""
        text = self.texts.get("confirmation_later")
        markup = self.keyboards.back_confirm()

        message = await self._send_message(text, reply_markup=markup)
        await self.state.set_state(BroadcastUIState.confirmation_later)
        return message

    # =========================================================================
    # Action Methods
    # =========================================================================

    async def store_message(self, message: Message) -> None:
        """
        Store message data for broadcasting.

        Args:
            message: Message to store.
        """
        message_data = message.model_dump()
        await self._data_storage.set("message_data", message_data)

    async def update_message_buttons(
        self, reply_markup: InlineKeyboardMarkup | None
    ) -> None:
        """
        Update stored message with new reply markup.

        Args:
            reply_markup: New reply markup or None.
        """
        message_data = await self._data_storage.get("message_data")
        if message_data:
            if reply_markup:
                message_data["reply_markup"] = reply_markup.model_dump()
            else:
                message_data["reply_markup"] = None
            await self._data_storage.set("message_data", message_data)

    async def store_datetime(self, dt: datetime) -> None:
        """
        Store scheduled datetime.

        Args:
            dt: Datetime to store.
        """
        await self._data_storage.set("scheduled_datetime", dt)

    async def execute_broadcast_now(self) -> None:
        """Execute immediate broadcast."""
        state_data = await self.state.get_data()
        subscriber_ids = state_data.get("subscriber_ids", [])
        message_data = await self._data_storage.get("message_data")

        if not subscriber_ids or not message_data:
            return

        # Create async task for broadcast
        asyncio.create_task(
            self._run_broadcast(subscriber_ids, message_data)
        )

    async def schedule_broadcast(self) -> str | None:
        """
        Schedule broadcast for later.

        Returns:
            Task ID if scheduled successfully, None otherwise.
        """
        if not self.scheduler or not self.scheduler.is_configured:
            return None

        state_data = await self.state.get_data()
        subscriber_ids = state_data.get("subscriber_ids", [])
        message_data = await self._data_storage.get("message_data")
        scheduled_dt = await self._data_storage.get("scheduled_datetime")

        if not subscriber_ids or not message_data or not scheduled_dt:
            return None

        # Add job to scheduler
        from apscheduler.triggers.date import DateTrigger

        task_id = self.scheduler._generate_task_id()

        self.scheduler.scheduler.add_job(
            func=self._run_broadcast,
            trigger=DateTrigger(scheduled_dt),
            id=task_id,
            kwargs={
                "subscriber_ids": subscriber_ids,
                "message_data": message_data,
            },
        )

        return task_id

    async def delete_scheduled_broadcast(self, job_id: str) -> bool:
        """
        Delete a scheduled broadcast.

        Args:
            job_id: Job ID to delete.

        Returns:
            True if deleted successfully.
        """
        if not self.scheduler or not self.scheduler.is_configured:
            return False

        try:
            self.scheduler.scheduler.remove_job(job_id)
            return True
        except Exception:
            return False

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _run_broadcast(
        self,
        subscriber_ids: list[int],
        message_data: dict[str, Any],
    ) -> None:
        """
        Run broadcast to all subscribers.

        Args:
            subscriber_ids: List of subscriber IDs.
            message_data: Message data to broadcast.
        """
        # Notify start
        start_text = self.texts.get("broadcast_started")
        with suppress(TelegramBadRequest):
            await self.bot.send_message(self.user.id, text=start_text)

        # Execute broadcast
        successful = 0
        failed = 0

        for user_id in subscriber_ids:
            result = await send_message_copy(self.bot, user_id, message_data)
            if result:
                successful += 1
            else:
                failed += 1

        # Notify completion
        end_text = self.texts.get(
            "broadcast_completed",
            total=len(subscriber_ids),
            successful=successful,
            failed=failed,
        )
        with suppress(TelegramBadRequest):
            await self.bot.send_message(self.user.id, text=end_text)

    async def _send_message(
        self,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message:
        """
        Send message and delete previous UI message.

        Args:
            text: Message text.
            reply_markup: Reply markup.

        Returns:
            Sent message.
        """
        message = await self.bot.send_message(
            chat_id=self.user.id,
            text=text,
            reply_markup=reply_markup,
        )
        await self._delete_previous_message()
        await self.state.update_data(ui_message_id=message.message_id)
        return message

    async def _delete_previous_message(self) -> None:
        """Delete previous UI message."""
        state_data = await self.state.get_data()
        message_id = state_data.get("ui_message_id")

        if not message_id:
            return

        try:
            await self.bot.delete_message(
                chat_id=self.user.id,
                message_id=message_id,
            )
        except TelegramBadRequest as ex:
            if any(e in ex.message for e in MESSAGE_DELETE_ERRORS):
                try:
                    text = self.texts.get("outdated_text")
                    await self.bot.edit_message_text(
                        chat_id=self.user.id,
                        message_id=message_id,
                        text=text,
                    )
                except TelegramBadRequest as inner_ex:
                    if not any(e in inner_ex.message for e in MESSAGE_EDIT_ERRORS):
                        raise inner_ex

    async def delete_user_message(self, message: Message) -> None:
        """
        Delete a user's message.

        Args:
            message: Message to delete.
        """
        with suppress(TelegramBadRequest):
            await message.delete()
