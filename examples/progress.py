"""
Broadcasting with progress tracking.

Demonstrates:
- Using progress_callback to monitor broadcast status
- Editing a status message with live progress

Requirements:
    pip install aiogram-broadcast
"""

import asyncio

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis

from aiogram_broadcast import (
    BroadcastMiddleware,
    BroadcastResult,
    BroadcastService,
    RedisBroadcastStorage,
)

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789

router = Router()


@router.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def broadcast_handler(message: Message, broadcast_service: BroadcastService) -> None:
    if not message.reply_to_message:
        await message.reply("Reply to the message you want to broadcast")
        return

    status = await message.reply("Broadcasting: 0%")

    async def on_progress(current: int, total: int, result: BroadcastResult) -> None:
        pct = int(current / total * 100)
        await status.edit_text(
            f"Broadcasting: {pct}% ({current}/{total})\n"
            f"Sent: {result.successful} | Failed: {result.failed}"
        )

    result = await broadcast_service.broadcast_copy(
        from_chat_id=message.chat.id,
        message_id=message.reply_to_message.message_id,
        progress_callback=on_progress,
    )
    await status.edit_text(
        f"Done! {result.successful}/{result.total} sent\nSuccess rate: {result.success_rate:.1f}%"
    )


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
