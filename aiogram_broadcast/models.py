"""Data models for aiogram-broadcast."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SubscriberState(str, Enum):
    """State of subscriber in relation to the bot."""

    MEMBER = "member"
    KICKED = "kicked"


@dataclass
class Subscriber:
    """
    Represents a bot subscriber.

    Attributes:
        id: Telegram user ID.
        full_name: User's full name.
        username: User's username (without @) or None.
        language_code: User's language code or None.
        state: Subscription state (member/kicked).
        subscribed_at: Timestamp when user first interacted with bot.
    """

    id: int
    full_name: str
    username: str | None = None
    language_code: str | None = None
    state: SubscriberState = SubscriberState.MEMBER
    subscribed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data["state"] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Subscriber:
        """Create instance from dictionary."""
        if "state" in data and isinstance(data["state"], str):
            data["state"] = SubscriberState(data["state"])
        return cls(**data)

    @property
    def is_active(self) -> bool:
        """Check if subscriber is active (not kicked the bot)."""
        return self.state == SubscriberState.MEMBER


@dataclass
class BroadcastResult:
    """
    Result of a broadcast operation.

    Attributes:
        total: Total number of subscribers targeted.
        successful: Number of successfully sent messages.
        failed: Number of failed sends.
        blocked_users: List of user IDs who blocked the bot.
        errors: Dictionary mapping user_id to error message.
    """

    total: int = 0
    successful: int = 0
    failed: int = 0
    blocked_users: list[int] = field(default_factory=list)
    errors: dict[int, str] = field(default_factory=dict)

    def add_success(self) -> None:
        """Record a successful send."""
        self.successful += 1

    def add_failure(self, user_id: int, error: str, is_blocked: bool = False) -> None:
        """Record a failed send."""
        self.failed += 1
        self.errors[user_id] = error
        if is_blocked:
            self.blocked_users.append(user_id)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100


@dataclass
class BroadcastTask:
    """
    Represents a scheduled broadcast task.

    Attributes:
        id: Unique task identifier.
        content: Message content to broadcast.
        content_type: Type of content (text, photo, copy, etc.).
        scheduled_at: When the broadcast should be executed.
        created_at: When the task was created.
        kwargs: Additional parameters for the broadcast.
    """

    id: str
    content: Any
    content_type: str
    scheduled_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    kwargs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "content": self.content,
            "content_type": self.content_type,
            "scheduled_at": self.scheduled_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "kwargs": self.kwargs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BroadcastTask:
        """Create instance from dictionary."""
        data = data.copy()
        if isinstance(data.get("scheduled_at"), str):
            data["scheduled_at"] = datetime.fromisoformat(data["scheduled_at"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
