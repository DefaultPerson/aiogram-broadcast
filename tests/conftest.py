"""Shared test fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aiogram_broadcast.models import Subscriber, SubscriberState
from aiogram_broadcast.service import BroadcastService


@pytest.fixture
def bot() -> AsyncMock:
    b = AsyncMock()
    b.send_message = AsyncMock()
    b.send_photo = AsyncMock()
    b.copy_message = AsyncMock()
    b.delete_message = AsyncMock()
    return b


@pytest.fixture
def storage() -> AsyncMock:
    s = AsyncMock()
    s.get_all_subscriber_ids = AsyncMock(return_value=[1, 2, 3])
    s.get_subscribers_count = AsyncMock(return_value=3)
    s.update_subscriber_state = AsyncMock()
    s.get_subscriber = AsyncMock(return_value=None)
    s.add_subscriber = AsyncMock()
    s.update_subscriber = AsyncMock()
    s.delete_subscriber = AsyncMock()
    return s


@pytest.fixture
def service(bot: AsyncMock, storage: AsyncMock) -> BroadcastService:
    return BroadcastService(bot, storage, rate_limit=0)


@pytest.fixture
def subscriber() -> Subscriber:
    return Subscriber(
        id=123,
        full_name="Test User",
        username="testuser",
        language_code="en",
        state=SubscriberState.MEMBER,
    )


@pytest.fixture
def mock_redis() -> AsyncMock:
    r = AsyncMock()
    r.hset = AsyncMock(return_value=1)
    r.hget = AsyncMock(return_value=None)
    r.hdel = AsyncMock(return_value=0)
    r.hkeys = AsyncMock(return_value=[])
    r.hlen = AsyncMock(return_value=0)
    r.hscan = AsyncMock(return_value=(0, {}))
    r.aclose = AsyncMock()
    return r
