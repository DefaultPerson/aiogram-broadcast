"""Tests for broadcast middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Chat, ChatMemberBanned, ChatMemberMember, ChatMemberUpdated, User

from aiogram_broadcast.middleware import (
    BroadcastChatMemberMiddleware,
    BroadcastMiddleware,
)
from aiogram_broadcast.models import Subscriber, SubscriberState


def _make_user(user_id: int = 1, full_name: str = "Test", username: str | None = "test") -> User:
    return User(id=user_id, is_bot=False, first_name=full_name, username=username)


def _make_chat(chat_id: int = 1, chat_type: str = "private") -> Chat:
    return Chat(id=chat_id, type=chat_type)


def _make_chat_member_update(
    user: User,
    chat: Chat,
    old_status: str = "kicked",
    new_status: str = "member",
) -> ChatMemberUpdated:
    def _member(status: str) -> ChatMemberMember | ChatMemberBanned:
        if status in ("kicked", "left"):
            return ChatMemberBanned(user=user, status="kicked", until_date=0)
        return ChatMemberMember(user=user, status="member")

    return ChatMemberUpdated(
        chat=chat,
        from_user=user,
        date=0,
        old_chat_member=_member(old_status),
        new_chat_member=_member(new_status),
    )


class TestBroadcastMiddleware:
    @pytest.fixture
    def mw(self, storage: AsyncMock) -> BroadcastMiddleware:
        return BroadcastMiddleware(storage)

    async def test_creates_new_subscriber(
        self, mw: BroadcastMiddleware, storage: AsyncMock
    ) -> None:
        handler = AsyncMock()
        data: dict = {"event_chat": _make_chat(), "event_from_user": _make_user()}
        storage.get_subscriber.return_value = None

        await mw(handler, MagicMock(), data)

        storage.add_subscriber.assert_called_once()
        assert data["subscriber"] is not None
        assert data["subscriber"].id == 1
        handler.assert_called_once()

    async def test_updates_changed_name(self, mw: BroadcastMiddleware, storage: AsyncMock) -> None:
        existing = Subscriber(id=1, full_name="Old Name", username="test")
        storage.get_subscriber.return_value = existing
        handler = AsyncMock()
        data: dict = {
            "event_chat": _make_chat(),
            "event_from_user": _make_user(full_name="New Name"),
        }

        await mw(handler, MagicMock(), data)

        storage.update_subscriber.assert_called_once()
        assert existing.full_name == "New Name"

    async def test_reactivates_kicked_user(
        self, mw: BroadcastMiddleware, storage: AsyncMock
    ) -> None:
        existing = Subscriber(id=1, full_name="Test", state=SubscriberState.KICKED)
        storage.get_subscriber.return_value = existing
        handler = AsyncMock()
        data: dict = {"event_chat": _make_chat(), "event_from_user": _make_user()}

        await mw(handler, MagicMock(), data)

        assert existing.state == SubscriberState.MEMBER
        storage.update_subscriber.assert_called_once()

    async def test_skips_non_private_chat(
        self, mw: BroadcastMiddleware, storage: AsyncMock
    ) -> None:
        handler = AsyncMock()
        data: dict = {
            "event_chat": _make_chat(chat_type="group"),
            "event_from_user": _make_user(),
        }

        await mw(handler, MagicMock(), data)

        assert data["subscriber"] is None
        storage.get_subscriber.assert_not_called()


class TestBroadcastChatMemberMiddleware:
    async def test_subscribe_calls_callback(self, storage: AsyncMock) -> None:
        on_subscribe = AsyncMock()
        mw = BroadcastChatMemberMiddleware(storage, on_subscribe=on_subscribe)
        handler = AsyncMock()
        user = _make_user()
        chat = _make_chat()
        event = _make_chat_member_update(user, chat, old_status="kicked", new_status="member")
        data: dict = {}
        storage.get_subscriber.return_value = None

        await mw(handler, event, data)

        on_subscribe.assert_called_once()
        sub = on_subscribe.call_args[0][0]
        assert sub.state == SubscriberState.MEMBER

    async def test_unsubscribe_calls_callback(self, storage: AsyncMock) -> None:
        on_unsubscribe = AsyncMock()
        mw = BroadcastChatMemberMiddleware(storage, on_unsubscribe=on_unsubscribe)
        handler = AsyncMock()
        user = _make_user()
        chat = _make_chat()
        event = _make_chat_member_update(user, chat, old_status="member", new_status="kicked")
        data: dict = {}
        existing = Subscriber(id=1, full_name="Test", state=SubscriberState.MEMBER)
        storage.get_subscriber.return_value = existing

        await mw(handler, event, data)

        on_unsubscribe.assert_called_once()
        assert existing.state == SubscriberState.KICKED

    async def test_no_change_passes_through(self, storage: AsyncMock) -> None:
        mw = BroadcastChatMemberMiddleware(storage)
        handler = AsyncMock()
        user = _make_user()
        chat = _make_chat()
        event = _make_chat_member_update(user, chat, old_status="member", new_status="member")
        data: dict = {}

        await mw(handler, event, data)

        handler.assert_called_once()
        storage.get_subscriber.assert_not_called()
