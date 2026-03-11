"""Middleware for broadcast UI manager injection."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import Chat, TelegramObject, User

from aiogram_broadcast.ui.keyboards import BroadcastUIKeyboards
from aiogram_broadcast.ui.manager import BroadcastUIManager
from aiogram_broadcast.ui.texts import BroadcastUITexts

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

    from aiogram_broadcast.scheduler import BroadcastScheduler
    from aiogram_broadcast.service import BroadcastService


class BroadcastUIMiddleware(BaseMiddleware):
    """
    Middleware for injecting BroadcastUIManager into handler data.

    This middleware creates a BroadcastUIManager instance for each
    private chat update and injects it into the handler data.

    Injects into handler data:
    - `broadcast_ui`: BroadcastUIManager instance (or None for non-private chats)

    Usage:
        from aiogram_broadcast import BroadcastService, BroadcastScheduler
        from aiogram_broadcast.ui import BroadcastUIMiddleware, BroadcastUIHandlers

        # Create service and scheduler
        service = BroadcastService(bot, storage)
        scheduler = BroadcastScheduler(service, apscheduler)

        # Register middleware
        dp.update.middleware.register(
            BroadcastUIMiddleware(service, scheduler)
        )

        # Register handlers
        BroadcastUIHandlers().register(dp)

        # In your command handler:
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
        service: BroadcastService,
        scheduler: BroadcastScheduler | None = None,
        texts: BroadcastUITexts | None = None,
        keyboards: BroadcastUIKeyboards | None = None,
        manager_key: str = "broadcast_ui",
    ) -> None:
        """
        Initialize middleware.

        Args:
            service: BroadcastService instance.
            scheduler: Optional BroadcastScheduler for scheduled broadcasts.
            texts: Optional custom texts (auto-created from user language if None).
            keyboards: Optional custom keyboards (auto-created from user language if None).
            manager_key: Key to inject manager into handler data.
        """
        self._service = service
        self._scheduler = scheduler
        self._texts = texts
        self._keyboards = keyboards
        self._manager_key = manager_key

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process update and inject BroadcastUIManager."""
        chat: Chat | None = data.get("event_chat")
        user: User | None = data.get("event_from_user")

        manager = None

        # Only process private chats
        if chat is not None and chat.type == "private" and user is not None:
            state: FSMContext | None = data.get("state")
            bot: Bot | None = data.get("bot")

            if state is None or bot is None:
                data[self._manager_key] = manager
                return await handler(event, data)

            # Get language from state or user
            state_data = await state.get_data()
            language_code = state_data.get("ui_language_code") or user.language_code

            # Create texts and keyboards with language
            texts = self._texts or BroadcastUITexts(language_code)
            keyboards = self._keyboards or BroadcastUIKeyboards(language_code)

            # Create manager
            manager = BroadcastUIManager(
                bot=bot,
                user=user,
                state=state,
                service=self._service,
                scheduler=self._scheduler,
                texts=texts,
                keyboards=keyboards,
                middleware_data=data,
            )

        data[self._manager_key] = manager
        return await handler(event, data)
