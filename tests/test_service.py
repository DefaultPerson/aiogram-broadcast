"""Tests for BroadcastService."""

from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramForbiddenError

from aiogram_broadcast.exceptions import BroadcastInProgressError
from aiogram_broadcast.models import SubscriberState
from aiogram_broadcast.service import BroadcastService


@pytest.fixture
def storage() -> AsyncMock:
    s = AsyncMock()
    s.get_all_subscriber_ids = AsyncMock(return_value=[1, 2, 3])
    s.get_subscribers_count = AsyncMock(return_value=3)
    s.update_subscriber_state = AsyncMock()
    return s


@pytest.fixture
def bot() -> AsyncMock:
    b = AsyncMock()
    b.send_message = AsyncMock()
    b.send_photo = AsyncMock()
    b.copy_message = AsyncMock()
    return b


@pytest.fixture
def service(bot: AsyncMock, storage: AsyncMock) -> BroadcastService:
    return BroadcastService(bot, storage, rate_limit=0)


async def test_broadcast_text(service: BroadcastService, bot: AsyncMock) -> None:
    result = await service.broadcast_text("Hello!")
    assert result.total == 3
    assert result.successful == 3
    assert result.failed == 0
    assert bot.send_message.call_count == 3


async def test_broadcast_photo(service: BroadcastService, bot: AsyncMock) -> None:
    result = await service.broadcast_photo("photo_id", caption="cap")
    assert result.total == 3
    assert result.successful == 3
    assert bot.send_photo.call_count == 3


async def test_broadcast_copy(service: BroadcastService, bot: AsyncMock) -> None:
    result = await service.broadcast_copy(from_chat_id=100, message_id=1)
    assert result.total == 3
    assert result.successful == 3
    assert bot.copy_message.call_count == 3


async def test_broadcast_custom(service: BroadcastService) -> None:
    sender = AsyncMock()
    result = await service.broadcast_custom(sender)
    assert result.total == 3
    assert sender.call_count == 3


async def test_broadcast_handles_blocked_user(
    service: BroadcastService, bot: AsyncMock, storage: AsyncMock
) -> None:
    error = TelegramForbiddenError(
        method=type("M", (), {"__name__": "send_message"})(),
        message="Forbidden: bot was blocked by the user",
    )
    bot.send_message.side_effect = [None, error, None]

    result = await service.broadcast_text("Hello!")
    assert result.successful == 2
    assert result.failed == 1
    assert 2 in result.blocked_users
    storage.update_subscriber_state.assert_called_once_with(2, SubscriberState.KICKED)


async def test_broadcast_in_progress_raises(service: BroadcastService) -> None:
    service._in_progress = True
    with pytest.raises(BroadcastInProgressError):
        await service.broadcast_text("test")


async def test_in_progress_flag_reset_on_error(
    service: BroadcastService, storage: AsyncMock
) -> None:
    storage.get_all_subscriber_ids.side_effect = RuntimeError("db error")
    with pytest.raises(RuntimeError):
        await service.broadcast_text("test")
    assert service.is_broadcasting is False


async def test_get_subscriber_count(service: BroadcastService, storage: AsyncMock) -> None:
    count = await service.get_subscriber_count(only_active=True)
    assert count == 3
    storage.get_subscribers_count.assert_called_once_with(state=SubscriberState.MEMBER)


async def test_properties(service: BroadcastService, bot: AsyncMock, storage: AsyncMock) -> None:
    assert service.bot is bot
    assert service.storage is storage
    assert service.is_broadcasting is False
