# aiogram-broadcast

Библиотека для рассылок в Telegram ботах на aiogram 3.x.

## Возможности

- Автоматическая регистрация подписчиков через middleware
- Rate-limited рассылка для избежания лимитов Telegram API
- Отложенные рассылки с APScheduler
- Redis хранилище подписчиков
- Callback'и для отслеживания прогресса
- Отслеживание заблокировавших бота пользователей

## Установка

```bash
pip install aiogram-broadcast
```

Или с поддержкой отложенных рассылок:

```bash
pip install aiogram-broadcast[scheduler]
```

## Быстрый старт

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

# Конфигурация
BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789  # Ваш Telegram ID

# Роутер
router = Router()


@router.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def broadcast_handler(
    message: Message,
    broadcast_service: BroadcastService,
) -> None:
    """Рассылка сообщения всем подписчикам."""
    if not message.reply_to_message:
        await message.reply("Ответьте на сообщение, которое хотите разослать")
        return

    # Показываем статус
    status_msg = await message.reply("Начинаю рассылку...")

    # Отправляем рассылку
    result = await broadcast_service.broadcast_copy(
        from_chat_id=message.chat.id,
        message_id=message.reply_to_message.message_id,
    )

    # Показываем результат
    await status_msg.edit_text(
        f"Рассылка завершена\n\n"
        f"Успешно: {result.successful}/{result.total}\n"
        f"Ошибок: {result.failed}\n"
        f"Заблокировали бота: {len(result.blocked_users)}"
    )


@router.message(Command("stats"), F.from_user.id == ADMIN_ID)
async def stats_handler(
    message: Message,
    broadcast_service: BroadcastService,
) -> None:
    """Статистика подписчиков."""
    total = await broadcast_service.get_subscriber_count(only_active=False)
    active = await broadcast_service.get_subscriber_count(only_active=True)

    await message.reply(
        f"Всего подписчиков: {total}\n"
        f"Активных: {active}\n"
        f"Заблокировали: {total - active}"
    )


async def main() -> None:
    # Инициализация
    redis = Redis(host="localhost", port=6379, db=0)
    storage = RedisBroadcastStorage(redis)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Создаём сервис рассылки
    broadcast_service = BroadcastService(bot, storage)

    # Регистрируем middleware для автоматической регистрации подписчиков
    dp.update.outer_middleware.register(BroadcastMiddleware(storage))

    # Добавляем broadcast_service в workflow_data для доступа в handlers
    dp["broadcast_service"] = broadcast_service

    # Подключаем роутер
    dp.include_router(router)

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

## Использование

### Middleware

`BroadcastMiddleware` автоматически:
- Регистрирует новых пользователей как подписчиков
- Обновляет информацию о подписчиках при каждом взаимодействии
- Отслеживает subscribe/unsubscribe события

```python
from aiogram_broadcast import BroadcastMiddleware, RedisBroadcastStorage

storage = RedisBroadcastStorage(redis)
dp.update.outer_middleware.register(BroadcastMiddleware(storage))
```

В handlers становятся доступны:
- `subscriber` - объект `Subscriber` (или `None` для не-приватных чатов)
- `broadcast_storage` - хранилище подписчиков

### BroadcastService

Основной сервис для отправки рассылок:

```python
from aiogram_broadcast import BroadcastService

service = BroadcastService(
    bot=bot,
    storage=storage,
    rate_limit=0.05,  # 20 сообщений в секунду
)

# Текстовая рассылка
result = await service.broadcast_text(
    text="Привет всем!",
    parse_mode="HTML",
)

# Рассылка фото
result = await service.broadcast_photo(
    photo="AgACAgIAAxk...",  # file_id
    caption="Описание фото",
)

# Копирование сообщения
result = await service.broadcast_copy(
    from_chat_id=admin_chat_id,
    message_id=message_id,
)
```

### Отложенные рассылки

```python
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram_broadcast import BroadcastScheduler

scheduler = AsyncIOScheduler()
broadcast_scheduler = BroadcastScheduler(
    service=broadcast_service,
    scheduler=scheduler,
)

# Запланировать рассылку через час
task_id = await broadcast_scheduler.schedule_text(
    text="Напоминание!",
    run_date=datetime.now() + timedelta(hours=1),
)

# Отменить рассылку
await broadcast_scheduler.cancel(task_id)

# Получить список запланированных рассылок
pending = broadcast_scheduler.get_pending_tasks()
```

### Callback прогресса

```python
async def progress_callback(current: int, total: int, result: BroadcastResult) -> None:
    print(f"Прогресс: {current}/{total} ({result.successful} успешно)")

result = await service.broadcast_text(
    text="Сообщение",
    progress_callback=progress_callback,
)
```

### BroadcastResult

```python
result = await service.broadcast_text("Hello!")

print(f"Всего: {result.total}")
print(f"Успешно: {result.successful}")
print(f"Ошибок: {result.failed}")
print(f"Заблокировали бота: {result.blocked_users}")
print(f"Процент успеха: {result.success_rate:.1f}%")
```

## API Reference

### Models

- `Subscriber` - модель подписчика
- `SubscriberState` - состояние подписчика (MEMBER/KICKED)
- `BroadcastResult` - результат рассылки
- `BroadcastTask` - задача отложенной рассылки

### Storage

- `BaseBroadcastStorage` - абстрактный класс хранилища
- `RedisBroadcastStorage` - Redis реализация

### Middleware

- `BroadcastMiddleware` - основной middleware
- `BroadcastChatMemberMiddleware` - для обработки только chat member updates

### Service

- `BroadcastService` - сервис рассылок
- `BroadcastScheduler` - планировщик рассылок

## Лицензия

MIT
