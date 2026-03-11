"""Tests for exceptions."""

from aiogram_broadcast.exceptions import (
    BroadcastError,
    BroadcastInProgressError,
    SchedulerNotConfiguredError,
    StorageError,
)


def test_hierarchy() -> None:
    assert issubclass(StorageError, BroadcastError)
    assert issubclass(BroadcastInProgressError, BroadcastError)
    assert issubclass(SchedulerNotConfiguredError, BroadcastError)


def test_broadcast_error_message() -> None:
    err = BroadcastError("test")
    assert str(err) == "test"


def test_storage_error_is_broadcast_error() -> None:
    err = StorageError("db fail")
    assert isinstance(err, BroadcastError)
