"""Utility functions for broadcast UI."""

from __future__ import annotations

import pickle
import re
from contextlib import suppress
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import Message

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext

# Error messages for message operations
MESSAGE_EDIT_ERRORS = [
    "no text in the message",
    "message can't be edited",
    "message is not modified",
    "message to edit not found",
]

MESSAGE_DELETE_ERRORS = [
    "message can't be deleted",
    "message to delete not found",
]


def validate_url(url: str) -> str | None:
    """
    Validate and extract URL from string.

    Args:
        url: URL string to validate.

    Returns:
        Valid URL or None.
    """
    url_pattern = re.compile(r"https?://\S+|www\.\S+")
    matches = re.findall(url_pattern, url)
    return matches[0] if matches else None


def validate_datetime(datetime_string: str) -> datetime | None:
    """
    Parse datetime string in format YYYY-MM-DD HH:MM.

    Args:
        datetime_string: Date/time string to parse.

    Returns:
        datetime object or None if parsing fails.
    """
    try:
        return datetime.strptime(datetime_string.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


class DataStorage:
    """
    Helper class for storing complex data in FSM state.

    Uses pickle to serialize any Python object to hex string
    for storage in FSM state data.
    """

    def __init__(self, state: FSMContext) -> None:
        """
        Initialize data storage.

        Args:
            state: FSM context for storing data.
        """
        self.state = state

    @staticmethod
    def _to_hex(data: Any) -> str:
        """Serialize data to hex string."""
        return pickle.dumps(data).hex()

    @staticmethod
    def _from_hex(hex_string: str) -> Any:
        """Deserialize data from hex string."""
        return pickle.loads(bytes.fromhex(hex_string))

    async def set(self, key: str, data: Any) -> None:
        """
        Store data in FSM state.

        Args:
            key: Storage key.
            data: Any picklable Python object.
        """
        await self.state.update_data(**{key: self._to_hex(data)})

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve data from FSM state.

        Args:
            key: Storage key.
            default: Default value if key not found.

        Returns:
            Stored data or default.
        """
        state_data = await self.state.get_data()
        hex_data = state_data.get(key)
        if hex_data is None:
            return default
        try:
            return self._from_hex(hex_data)
        except Exception:
            return default

    async def delete(self, key: str) -> None:
        """
        Delete data from FSM state.

        Args:
            key: Storage key to delete.
        """
        state_data = await self.state.get_data()
        if key in state_data:
            state_data.pop(key)
            await self.state.set_data(state_data)


async def send_message_copy(
    bot: Bot,
    chat_id: int,
    message_data: dict[str, Any],
) -> bool:
    """
    Send a copy of a message to a chat.

    Recreates a Message object from stored data and sends a copy.

    Args:
        bot: Bot instance.
        chat_id: Target chat ID.
        message_data: Serialized message data from Message.model_dump().

    Returns:
        True if message was sent successfully.
    """
    try:
        message_obj = Message(**message_data).as_(bot)
        await message_obj.send_copy(
            chat_id=chat_id,
            reply_markup=message_obj.reply_markup,
        )
        return True
    except TelegramRetryAfter as e:
        import asyncio

        await asyncio.sleep(e.retry_after)
        return await send_message_copy(bot, chat_id, message_data)
    except TelegramBadRequest:
        return False
    except Exception:
        return False


async def delete_message_safe(message: Message) -> bool:
    """
    Safely delete a message, ignoring errors.

    Args:
        message: Message to delete.

    Returns:
        True if deleted successfully.
    """
    with suppress(TelegramBadRequest):
        await message.delete()
        return True
    return False


async def delete_message_by_id(
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> bool:
    """
    Safely delete a message by ID.

    Args:
        bot: Bot instance.
        chat_id: Chat ID.
        message_id: Message ID to delete.

    Returns:
        True if deleted successfully.
    """
    with suppress(TelegramBadRequest):
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    return False
