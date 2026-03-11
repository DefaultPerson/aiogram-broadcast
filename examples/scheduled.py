"""
Scheduled broadcasts with APScheduler.

Demonstrates:
- Scheduling broadcasts for a specific time
- Listing and cancelling pending broadcasts

Requirements:
    pip install aiogram-broadcast[scheduler]
"""

import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis.asyncio import Redis

from aiogram_broadcast import (
    BroadcastMiddleware,
    BroadcastScheduler,
    BroadcastService,
    RedisBroadcastStorage,
)

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789

router = Router()


@router.message(Command("schedule"), F.from_user.id == ADMIN_ID)
async def schedule_handler(message: Message, broadcast_scheduler: BroadcastScheduler) -> None:
    """Schedule a text broadcast in 1 hour."""
    task_id = await broadcast_scheduler.schedule_text(
        text="Scheduled message!",
        run_date=datetime.now() + timedelta(hours=1),
    )
    await message.reply(f"Scheduled: {task_id}")


@router.message(Command("pending"), F.from_user.id == ADMIN_ID)
async def pending_handler(message: Message, broadcast_scheduler: BroadcastScheduler) -> None:
    """List pending broadcasts."""
    tasks = broadcast_scheduler.get_pending_tasks()
    if not tasks:
        await message.reply("No pending broadcasts")
        return
    lines = [f"- {t.id}: {t.content_type} at {t.scheduled_at}" for t in tasks]
    await message.reply("\n".join(lines))


@router.message(Command("cancel"), F.from_user.id == ADMIN_ID)
async def cancel_handler(message: Message, broadcast_scheduler: BroadcastScheduler) -> None:
    """Cancel a broadcast by ID: /cancel broadcast_abc123"""
    args = message.text.split(maxsplit=1) if message.text else []
    if len(args) < 2:
        await message.reply("Usage: /cancel <task_id>")
        return
    ok = await broadcast_scheduler.cancel(args[1])
    await message.reply("Cancelled" if ok else "Not found")


async def main() -> None:
    redis = Redis(host="localhost")
    storage = RedisBroadcastStorage(redis)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    service = BroadcastService(bot, storage)
    apscheduler = AsyncIOScheduler()
    scheduler = BroadcastScheduler(service, apscheduler)

    dp.update.outer_middleware.register(BroadcastMiddleware(storage))
    dp["broadcast_service"] = service
    dp["broadcast_scheduler"] = scheduler
    dp.include_router(router)

    apscheduler.start()
    try:
        await dp.start_polling(bot)
    finally:
        apscheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
