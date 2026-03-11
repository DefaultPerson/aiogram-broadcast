# aiogram-broadcast

[![PyPI](https://img.shields.io/pypi/v/aiogram-broadcast)](https://pypi.org/project/aiogram-broadcast/)
[![CI](https://github.com/DefaultPerson/aiogram-broadcast/actions/workflows/ci.yml/badge.svg)](https://github.com/DefaultPerson/aiogram-broadcast/actions/workflows/ci.yml)

Broadcast/newsletter library for Telegram bots built with aiogram 3.x.

## Features

- Automatic subscriber registration via middleware
- Rate-limited broadcasting to avoid Telegram API limits
- Scheduled broadcasts with APScheduler
- Redis subscriber storage
- Progress callbacks for monitoring
- Interactive UI menu with multi-language support (EN/RU)

## Installation

```bash
pip install aiogram-broadcast
```

With scheduled broadcasts and UI:

```bash
pip install aiogram-broadcast[all]
```

## Quick Start

```python
from aiogram_broadcast import BroadcastMiddleware, BroadcastService, RedisBroadcastStorage

redis = Redis(host="localhost")
storage = RedisBroadcastStorage(redis)
service = BroadcastService(bot, storage)

# Auto-register subscribers
dp.update.outer_middleware.register(BroadcastMiddleware(storage))

# Broadcast to all
result = await service.broadcast_text("Hello everyone!", parse_mode="HTML")
print(f"{result.successful}/{result.total} sent, {result.success_rate:.0f}%")
```

See [examples/basic.py](examples/basic.py) for a complete runnable bot.

## Usage

### Broadcasting

```python
# Text, photo, video, document, or copy any message
await service.broadcast_text("Hello!", parse_mode="HTML")
await service.broadcast_photo(photo_file_id, caption="Check this out")
await service.broadcast_copy(from_chat_id=admin_id, message_id=msg_id)

# Custom sender for any message type
await service.broadcast_custom(my_sender_func)
```

### Scheduled Broadcasts

```python
from aiogram_broadcast import BroadcastScheduler

scheduler = BroadcastScheduler(service, AsyncIOScheduler())
task_id = await scheduler.schedule_text("Reminder!", run_date=some_datetime)
await scheduler.cancel(task_id)
```

See [examples/scheduled.py](examples/scheduled.py) for full setup.

### Progress Tracking

```python
async def on_progress(current, total, result):
    print(f"{current}/{total} — {result.successful} sent, {result.failed} failed")

await service.broadcast_text("msg", progress_callback=on_progress)
```

See [examples/progress.py](examples/progress.py).

### Interactive UI Menu

A complete FSM-based wizard for composing and scheduling broadcasts from Telegram — supports text/photo/video/document messages, inline URL buttons, and scheduled delivery.

See [examples/ui_menu.py](examples/ui_menu.py).

## License

MIT
