"""
Basic broadcast bot.

Demonstrates:
- Automatic subscriber registration via middleware
- Broadcasting a message to all subscribers
- Subscriber statistics

Requirements:
    pip install aiogram-broadcast
"""

import asyncio

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis

from aiogram_broadcast import BroadcastMiddleware, BroadcastService, RedisBroadcastStorage

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789

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
    redis = Redis(host="localhost")
    storage = RedisBroadcastStorage(redis)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.update.outer_middleware.register(BroadcastMiddleware(storage))
    dp["broadcast_service"] = BroadcastService(bot, storage)
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
