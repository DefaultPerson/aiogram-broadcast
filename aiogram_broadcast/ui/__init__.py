"""
Broadcast UI module for aiogram-broadcast.

Provides a complete interactive menu for creating and managing broadcasts
with support for:
- Text, photo, video, and document messages
- Inline URL buttons
- Scheduled broadcasts
- Multi-language support (EN/RU)

Quick Start:
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.redis import RedisStorage
    from redis.asyncio import Redis
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from aiogram_broadcast import (
        BroadcastMiddleware,
        BroadcastService,
        BroadcastScheduler,
        RedisBroadcastStorage,
    )
    from aiogram_broadcast.ui import (
        BroadcastUIMiddleware,
        BroadcastUIHandlers,
    )

    # Setup
    redis = Redis()
    storage = RedisBroadcastStorage(redis)
    fsm_storage = RedisStorage(redis)

    bot = Bot(token="YOUR_TOKEN")
    dp = Dispatcher(storage=fsm_storage)

    # Create service and scheduler
    apscheduler = AsyncIOScheduler()
    service = BroadcastService(bot, storage)
    scheduler = BroadcastScheduler(service, apscheduler)

    # Register middlewares
    dp.update.outer_middleware.register(BroadcastMiddleware(storage))
    dp.update.middleware.register(BroadcastUIMiddleware(service, scheduler))

    # Register UI handlers
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

from aiogram_broadcast.ui.handlers import BroadcastUIHandlers
from aiogram_broadcast.ui.keyboards import BroadcastUIKeyboards, InlineKeyboardPaginator
from aiogram_broadcast.ui.manager import BroadcastUIManager
from aiogram_broadcast.ui.middleware import BroadcastUIMiddleware
from aiogram_broadcast.ui.states import BroadcastUIState
from aiogram_broadcast.ui.texts import BroadcastUITexts
from aiogram_broadcast.ui.utils import (
    DataStorage,
    delete_message_by_id,
    delete_message_safe,
    send_message_copy,
    validate_datetime,
    validate_url,
)

__all__ = [
    # Main classes
    "BroadcastUIManager",
    "BroadcastUIMiddleware",
    "BroadcastUIHandlers",
    # States
    "BroadcastUIState",
    # UI components
    "BroadcastUITexts",
    "BroadcastUIKeyboards",
    "InlineKeyboardPaginator",
    # Utilities
    "DataStorage",
    "validate_url",
    "validate_datetime",
    "send_message_copy",
    "delete_message_safe",
    "delete_message_by_id",
]
