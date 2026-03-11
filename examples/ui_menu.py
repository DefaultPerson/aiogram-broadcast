"""
Interactive broadcast UI menu.

Demonstrates:
- Full interactive menu for creating broadcasts
- FSM-based wizard: compose message → add buttons → preview → send/schedule
- Multi-language support (auto-detected from user's Telegram language)

Requirements:
    pip install aiogram-broadcast[ui]
"""

import asyncio

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis.asyncio import Redis

from aiogram_broadcast import (
    BroadcastMiddleware,
    BroadcastScheduler,
    BroadcastService,
    RedisBroadcastStorage,
)
from aiogram_broadcast.ui import BroadcastUIHandlers, BroadcastUIManager, BroadcastUIMiddleware

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789

router = Router()


@router.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def broadcast_command(
    message: Message,
    broadcast_ui: BroadcastUIManager,
    broadcast_storage: BroadcastService,
) -> None:
    """Open the interactive broadcast menu."""
    subscriber_ids = await broadcast_storage.storage.get_all_subscriber_ids()
    await broadcast_ui.open_menu(subscriber_ids)
    await message.delete()


async def main() -> None:
    redis = Redis(host="localhost")
    storage = RedisBroadcastStorage(redis)
    fsm_storage = RedisStorage(redis)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=fsm_storage)

    service = BroadcastService(bot, storage)
    apscheduler = AsyncIOScheduler()
    scheduler = BroadcastScheduler(service, apscheduler)

    # Subscriber tracking
    dp.update.outer_middleware.register(BroadcastMiddleware(storage))
    # UI manager injection
    dp.update.middleware.register(BroadcastUIMiddleware(service, scheduler))
    # UI FSM handlers
    BroadcastUIHandlers().register(dp)

    dp["broadcast_service"] = service
    dp.include_router(router)

    apscheduler.start()
    try:
        await dp.start_polling(bot)
    finally:
        apscheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
