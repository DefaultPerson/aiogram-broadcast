"""
aiogram-broadcast - Broadcast/newsletter library for aiogram 3.x

A pluggable library for managing subscribers and broadcasting messages
in Telegram bots built with aiogram.

Features:
- Automatic subscriber registration via middleware
- Rate-limited broadcasting to avoid API limits
- Scheduled broadcasts with APScheduler integration
- Redis storage for subscribers
- Progress callbacks for monitoring broadcasts
- Interactive UI menu for creating broadcasts (see aiogram_broadcast.ui)

Quick Start:
    from aiogram import Bot, Dispatcher
    from redis.asyncio import Redis
    from aiogram_broadcast import (
        BroadcastMiddleware,
        BroadcastService,
        RedisBroadcastStorage,
    )

    # Setup
    redis = Redis()
    storage = RedisBroadcastStorage(redis)
    bot = Bot(token="YOUR_TOKEN")
    dp = Dispatcher()

    # Register middleware
    dp.update.outer_middleware.register(BroadcastMiddleware(storage))

    # Create service
    broadcast = BroadcastService(bot, storage)

    # Broadcast to all subscribers
    result = await broadcast.broadcast_text("Hello everyone!")
    print(f"Sent to {result.successful}/{result.total} users")

Interactive UI:
    For a complete interactive menu, see the `aiogram_broadcast.ui` module:

    from aiogram_broadcast.ui import (
        BroadcastUIMiddleware,
        BroadcastUIHandlers,
        BroadcastUIManager,
    )
"""

__version__ = "0.1.0"
__author__ = "DefaultPerson"

from aiogram_broadcast.exceptions import (
    BroadcastError,
    BroadcastInProgressError,
    SchedulerNotConfiguredError,
    StorageError,
)
from aiogram_broadcast.middleware import (
    BroadcastChatMemberMiddleware,
    BroadcastMiddleware,
)
from aiogram_broadcast.models import (
    BroadcastResult,
    BroadcastTask,
    Subscriber,
    SubscriberState,
)
from aiogram_broadcast.scheduler import BroadcastScheduler
from aiogram_broadcast.service import BroadcastService
from aiogram_broadcast.storage import (
    BaseBroadcastStorage,
    RedisBroadcastStorage,
)

__all__ = [
    # Version
    "__version__",
    # Middleware
    "BroadcastMiddleware",
    "BroadcastChatMemberMiddleware",
    # Service
    "BroadcastService",
    "BroadcastScheduler",
    # Models
    "Subscriber",
    "SubscriberState",
    "BroadcastResult",
    "BroadcastTask",
    # Storage
    "BaseBroadcastStorage",
    "RedisBroadcastStorage",
    # Exceptions
    "BroadcastError",
    "StorageError",
    "BroadcastInProgressError",
    "SchedulerNotConfiguredError",
]
