# aiogram-broadcast

Broadcast/newsletter library for Telegram bots built with aiogram 3.x.

## Features

- Automatic subscriber registration via middleware
- Rate-limited broadcasting to avoid Telegram API limits
- Scheduled broadcasts with APScheduler
- Redis subscriber storage
- Progress callbacks for monitoring
- Automatic tracking of users who blocked the bot

## Installation

```bash
pip install aiogram-broadcast
```

With scheduled broadcast support:

```bash
pip install aiogram-broadcast[scheduler]
```

## Quick Start

```python
import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis

from aiogram_broadcast import (
    BroadcastMiddleware,
    BroadcastService,
    RedisBroadcastStorage,
)

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789  # Your Telegram ID

router = Router()


@router.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def broadcast_handler(
    message: Message,
    broadcast_service: BroadcastService,
) -> None:
    """Broadcast a message to all subscribers."""
    if not message.reply_to_message:
        await message.reply("Reply to the message you want to broadcast")
        return

    status_msg = await message.reply("Starting broadcast...")

    result = await broadcast_service.broadcast_copy(
        from_chat_id=message.chat.id,
        message_id=message.reply_to_message.message_id,
    )

    await status_msg.edit_text(
        f"Broadcast completed\n\n"
        f"Successful: {result.successful}/{result.total}\n"
        f"Failed: {result.failed}\n"
        f"Blocked: {len(result.blocked_users)}"
    )


@router.message(Command("stats"), F.from_user.id == ADMIN_ID)
async def stats_handler(
    message: Message,
    broadcast_service: BroadcastService,
) -> None:
    """Subscriber statistics."""
    total = await broadcast_service.get_subscriber_count(only_active=False)
    active = await broadcast_service.get_subscriber_count(only_active=True)

    await message.reply(
        f"Total subscribers: {total}\n"
        f"Active: {active}\n"
        f"Blocked: {total - active}"
    )


async def main() -> None:
    redis = Redis(host="localhost", port=6379, db=0)
    storage = RedisBroadcastStorage(redis)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    broadcast_service = BroadcastService(bot, storage)

    # Register middleware for automatic subscriber tracking
    dp.update.outer_middleware.register(BroadcastMiddleware(storage))

    # Make broadcast_service available in handlers
    dp["broadcast_service"] = broadcast_service

    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

## Usage

### Middleware

`BroadcastMiddleware` automatically:
- Registers new users as subscribers
- Updates subscriber info on each interaction
- Tracks subscribe/unsubscribe events

```python
from aiogram_broadcast import BroadcastMiddleware, RedisBroadcastStorage

storage = RedisBroadcastStorage(redis)
dp.update.outer_middleware.register(BroadcastMiddleware(storage))
```

Injected into handler data:
- `subscriber` — `Subscriber` instance (or `None` for non-private chats)
- `broadcast_storage` — storage instance

### BroadcastService

Main service for sending broadcasts:

```python
from aiogram_broadcast import BroadcastService

service = BroadcastService(
    bot=bot,
    storage=storage,
    rate_limit=0.05,  # 20 messages per second
)

# Text broadcast
result = await service.broadcast_text(
    text="Hello everyone!",
    parse_mode="HTML",
)

# Photo broadcast
result = await service.broadcast_photo(
    photo="AgACAgIAAxk...",  # file_id
    caption="Photo caption",
)

# Copy message broadcast
result = await service.broadcast_copy(
    from_chat_id=admin_chat_id,
    message_id=message_id,
)
```

### Scheduled Broadcasts

```python
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram_broadcast import BroadcastScheduler

scheduler = AsyncIOScheduler()
broadcast_scheduler = BroadcastScheduler(
    service=broadcast_service,
    scheduler=scheduler,
)

# Schedule a broadcast in 1 hour
task_id = await broadcast_scheduler.schedule_text(
    text="Reminder!",
    run_date=datetime.now() + timedelta(hours=1),
)

# Cancel a scheduled broadcast
await broadcast_scheduler.cancel(task_id)

# List pending broadcasts
pending = broadcast_scheduler.get_pending_tasks()
```

### Progress Callback

```python
async def progress_callback(current: int, total: int, result: BroadcastResult) -> None:
    print(f"Progress: {current}/{total} ({result.successful} successful)")

result = await service.broadcast_text(
    text="Message",
    progress_callback=progress_callback,
)
```

### BroadcastResult

```python
result = await service.broadcast_text("Hello!")

print(f"Total: {result.total}")
print(f"Successful: {result.successful}")
print(f"Failed: {result.failed}")
print(f"Blocked: {result.blocked_users}")
print(f"Success rate: {result.success_rate:.1f}%")
```

## API Reference

### Models

- `Subscriber` — subscriber model
- `SubscriberState` — subscriber state (MEMBER/KICKED)
- `BroadcastResult` — broadcast result
- `BroadcastTask` — scheduled broadcast task

### Storage

- `BaseBroadcastStorage` — abstract storage class
- `RedisBroadcastStorage` — Redis implementation

### Middleware

- `BroadcastMiddleware` — main middleware
- `BroadcastChatMemberMiddleware` — for handling chat member updates only

### Service

- `BroadcastService` — broadcast service
- `BroadcastScheduler` — broadcast scheduler

## License

MIT
