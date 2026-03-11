"""Custom exceptions for aiogram-broadcast."""


class BroadcastError(Exception):
    """Base exception for broadcast-related errors."""
    pass


class StorageError(BroadcastError):
    """Error related to storage operations."""
    pass


class BroadcastInProgressError(BroadcastError):
    """Raised when trying to start a broadcast while another is in progress."""
    pass


class SchedulerNotConfiguredError(BroadcastError):
    """Raised when trying to use scheduler features without configuring APScheduler."""
    pass
