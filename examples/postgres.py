"""
Basic broadcast bot backed by PostgreSQL.

Demonstrates:
- Using PostgreSQL (asyncpg) instead of Redis for subscriber storage
- Automatic subscriber registration via middleware
- Broadcasting a message to all subscribers

Requirements:
    pip install aiogram-broadcast[postgres]
"""

import asyncio

import asyncpg
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from aiogram_broadcast import BroadcastMiddleware, BroadcastService, PostgresBroadcastStorage

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789
DATABASE_URL = "postgresql://user:password@localhost:5432/mydb"

router = Router()


@router.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def broadcast_handler(message: Message, broadcast_service: BroadcastService) -> None:
    if not message.reply_to_message:
        await message.reply("Reply to the message you want to broadcast")
        return

    status = await message.reply("Starting broadcast...")
    result = await broadcast_service.broadcast_copy(
        from_chat_id=message.chat.id,
        message_id=message.reply_to_message.message_id,
    )
    await status.edit_text(
        f"Done: {result.successful}/{result.total} sent, "
        f"{result.failed} failed, {len(result.blocked_users)} blocked"
    )


@router.message(Command("stats"), F.from_user.id == ADMIN_ID)
async def stats_handler(message: Message, broadcast_service: BroadcastService) -> None:
    total = await broadcast_service.get_subscriber_count(only_active=False)
    active = await broadcast_service.get_subscriber_count(only_active=True)
    await message.reply(f"Subscribers: {active} active / {total} total")


async def main() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL)
    storage = PostgresBroadcastStorage(pool)
    # Create the subscribers table and index once on startup.
    await storage.create_schema()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.update.outer_middleware.register(BroadcastMiddleware(storage))
    dp["broadcast_service"] = BroadcastService(bot, storage)
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
