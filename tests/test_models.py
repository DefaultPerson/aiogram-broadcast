"""Tests for data models."""

from datetime import datetime, timezone

from aiogram_broadcast.models import (
    BroadcastResult,
    BroadcastTask,
    Subscriber,
    SubscriberState,
)


class TestSubscriberState:
    def test_member_value(self) -> None:
        assert SubscriberState.MEMBER.value == "member"

    def test_kicked_value(self) -> None:
        assert SubscriberState.KICKED.value == "kicked"


class TestSubscriber:
    def test_create_minimal(self) -> None:
        sub = Subscriber(id=123, full_name="Test User")
        assert sub.id == 123
        assert sub.full_name == "Test User"
        assert sub.username is None
        assert sub.language_code is None
        assert sub.state == SubscriberState.MEMBER
        assert sub.subscribed_at is not None

    def test_create_full(self) -> None:
        sub = Subscriber(
            id=456,
            full_name="John Doe",
            username="johndoe",
            language_code="en",
            state=SubscriberState.KICKED,
        )
        assert sub.id == 456
        assert sub.username == "johndoe"
        assert sub.language_code == "en"
        assert sub.state == SubscriberState.KICKED

    def test_is_active(self) -> None:
        sub = Subscriber(id=1, full_name="Active")
        assert sub.is_active is True

        sub.state = SubscriberState.KICKED
        assert sub.is_active is False

    def test_to_dict(self) -> None:
        sub = Subscriber(id=1, full_name="Test", username="test", language_code="ru")
        data = sub.to_dict()
        assert data["id"] == 1
        assert data["full_name"] == "Test"
        assert data["username"] == "test"
        assert data["language_code"] == "ru"
        assert data["state"] == "member"

    def test_from_dict(self) -> None:
        data = {
            "id": 1,
            "full_name": "Test",
            "username": "test",
            "language_code": "ru",
            "state": "kicked",
            "subscribed_at": "2024-01-01T00:00:00+00:00",
        }
        sub = Subscriber.from_dict(data)
        assert sub.id == 1
        assert sub.state == SubscriberState.KICKED
        assert sub.subscribed_at == "2024-01-01T00:00:00+00:00"

    def test_roundtrip(self) -> None:
        original = Subscriber(id=42, full_name="Round Trip", username="rt")
        restored = Subscriber.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.full_name == original.full_name
        assert restored.username == original.username
        assert restored.state == original.state


class TestBroadcastResult:
    def test_initial_state(self) -> None:
        result = BroadcastResult()
        assert result.total == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.blocked_users == []
        assert result.errors == {}

    def test_add_success(self) -> None:
        result = BroadcastResult(total=10)
        result.add_success()
        result.add_success()
        assert result.successful == 2

    def test_add_failure(self) -> None:
        result = BroadcastResult(total=10)
        result.add_failure(123, "some error")
        assert result.failed == 1
        assert result.errors[123] == "some error"
        assert result.blocked_users == []

    def test_add_failure_blocked(self) -> None:
        result = BroadcastResult(total=10)
        result.add_failure(123, "bot was blocked", is_blocked=True)
        assert result.failed == 1
        assert 123 in result.blocked_users

    def test_success_rate(self) -> None:
        result = BroadcastResult(total=100, successful=75)
        assert result.success_rate == 75.0

    def test_success_rate_zero_total(self) -> None:
        result = BroadcastResult()
        assert result.success_rate == 0.0


class TestBroadcastTask:
    def test_create(self) -> None:
        dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        task = BroadcastTask(
            id="broadcast_abc",
            content="Hello!",
            content_type="text",
            scheduled_at=dt,
        )
        assert task.id == "broadcast_abc"
        assert task.content == "Hello!"
        assert task.content_type == "text"
        assert task.scheduled_at == dt

    def test_to_dict(self) -> None:
        dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        task = BroadcastTask(
            id="t1",
            content="msg",
            content_type="text",
            scheduled_at=dt,
        )
        data = task.to_dict()
        assert data["id"] == "t1"
        assert data["scheduled_at"] == "2024-06-01T12:00:00+00:00"

    def test_roundtrip(self) -> None:
        dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        original = BroadcastTask(
            id="t1",
            content="msg",
            content_type="text",
            scheduled_at=dt,
            kwargs={"parse_mode": "HTML"},
        )
        restored = BroadcastTask.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.content == original.content
        assert restored.scheduled_at == original.scheduled_at
        assert restored.kwargs == original.kwargs
