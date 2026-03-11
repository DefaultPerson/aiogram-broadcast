"""Handlers for broadcast UI menu."""

from __future__ import annotations

from aiogram import Dispatcher, F, Router
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message

from aiogram_broadcast.ui.keyboards import BroadcastUIKeyboards
from aiogram_broadcast.ui.manager import BroadcastUIManager
from aiogram_broadcast.ui.states import BroadcastUIState
from aiogram_broadcast.ui.utils import validate_datetime


class BroadcastUIHandlers:
    """
    Handler class for broadcast UI menu.

    Registers all necessary handlers for the broadcast UI flow:
    - Callback query handlers for button presses
    - Message handlers for user input

    Usage:
        handlers = BroadcastUIHandlers()
        handlers.register(dp)

        # Or with custom router:
        router = Router()
        handlers.register_on_router(router)
        dp.include_router(router)
    """

    # =========================================================================
    # Broadcasts List Handlers
    # =========================================================================

    @staticmethod
    async def _broadcasts_list_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in broadcasts list state."""
        if call.data == "back":
            await broadcast_ui.return_to_caller()
            await broadcast_ui._delete_previous_message()
        elif call.data == "add":
            await broadcast_ui.open_send_message()
        elif call.data and call.data.startswith("page:"):
            page = int(call.data.split(":")[1])
            await broadcast_ui.state.update_data(page=page)
            await broadcast_ui.open_broadcasts_list()
        elif call.data and call.data.startswith("job:"):
            job_id = call.data.split(":")[1]
            await broadcast_ui.state.update_data(job_id=job_id)
            await broadcast_ui.open_broadcast_view()

        await call.answer()

    @staticmethod
    async def _broadcasts_list_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle messages in broadcasts list state (delete them)."""
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Broadcast View Handlers
    # =========================================================================

    @staticmethod
    async def _broadcast_view_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in broadcast view state."""
        if call.data == "back":
            await broadcast_ui.open_broadcasts_list()
        elif call.data == "delete":
            await broadcast_ui.open_broadcast_delete()

        await call.answer()

    @staticmethod
    async def _broadcast_view_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle messages in broadcast view state (delete them)."""
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Broadcast Delete Handlers
    # =========================================================================

    @staticmethod
    async def _broadcast_delete_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in broadcast delete confirmation state."""
        if call.data == "back":
            await broadcast_ui.open_broadcast_view()
        elif call.data == "confirm":
            state_data = await broadcast_ui.state.get_data()
            job_id = state_data.get("job_id")
            if job_id:
                await broadcast_ui.delete_scheduled_broadcast(job_id)
            await broadcast_ui.open_broadcasts_list()

        await call.answer()

    @staticmethod
    async def _broadcast_delete_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle messages in broadcast delete state (delete them)."""
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Send Message Handlers
    # =========================================================================

    @staticmethod
    async def _send_message_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in send message state."""
        if call.data == "back":
            await broadcast_ui.open_broadcasts_list()

        await call.answer()

    @staticmethod
    async def _send_message_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle message input in send message state."""
        # Store the message data
        await broadcast_ui.store_message(message)
        # Move to buttons input
        await broadcast_ui.open_send_buttons()
        # Delete user's message
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Send Buttons Handlers
    # =========================================================================

    @staticmethod
    async def _send_buttons_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in send buttons state."""
        if call.data == "back":
            await broadcast_ui.open_send_message()
        elif call.data == "skip":
            # No buttons - proceed to preview
            await broadcast_ui.update_message_buttons(None)
            await broadcast_ui.open_message_preview()

        await call.answer()

    @staticmethod
    async def _send_buttons_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle button text input in send buttons state."""
        if message.text:
            # Try to parse buttons
            markup = BroadcastUIKeyboards.build_url_buttons(message.text)
            if markup:
                await broadcast_ui.update_message_buttons(markup)
                await broadcast_ui.open_message_preview()
            else:
                # Show error
                error_text = broadcast_ui.texts.get("send_buttons_error")
                await broadcast_ui.open_send_buttons(error_text)
        else:
            # Non-text message - show error
            error_text = broadcast_ui.texts.get("send_buttons_error")
            await broadcast_ui.open_send_buttons(error_text)

        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Message Preview Handlers
    # =========================================================================

    @staticmethod
    async def _message_preview_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in message preview state."""
        if call.data == "back":
            await broadcast_ui.open_send_buttons()
        elif call.data == "next":
            await broadcast_ui.open_choose_options()

        await call.answer()

    @staticmethod
    async def _message_preview_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle messages in message preview state (delete them)."""
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Choose Options Handlers
    # =========================================================================

    @staticmethod
    async def _choose_options_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in choose options state."""
        if call.data == "back":
            await broadcast_ui.open_message_preview()
        elif call.data == "now":
            await broadcast_ui.open_confirmation_now()
        elif call.data == "later":
            await broadcast_ui.open_send_datetime()

        await call.answer()

    @staticmethod
    async def _choose_options_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle messages in choose options state (delete them)."""
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Confirmation Now Handlers
    # =========================================================================

    @staticmethod
    async def _confirmation_now_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in confirmation now state."""
        if call.data == "back":
            await broadcast_ui.open_choose_options()
        elif call.data == "confirm":
            # Start broadcast
            await broadcast_ui.execute_broadcast_now()
            # Return to broadcasts list
            await broadcast_ui.open_broadcasts_list()

        await call.answer()

    @staticmethod
    async def _confirmation_now_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle messages in confirmation now state (delete them)."""
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Send Datetime Handlers
    # =========================================================================

    @staticmethod
    async def _send_datetime_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in send datetime state."""
        if call.data == "back":
            await broadcast_ui.open_choose_options()

        await call.answer()

    @staticmethod
    async def _send_datetime_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle datetime input in send datetime state."""
        if message.text:
            dt = validate_datetime(message.text)
            if dt:
                await broadcast_ui.store_datetime(dt)
                await broadcast_ui.open_confirmation_later()
            else:
                from datetime import datetime as dt_module

                datetime_string = dt_module.now().strftime("%Y-%m-%d %H:%M")
                error_text = broadcast_ui.texts.get(
                    "send_datetime_error", datetime_string=datetime_string
                )
                await broadcast_ui.open_send_datetime(error_text)
        else:
            from datetime import datetime as dt_module

            datetime_string = dt_module.now().strftime("%Y-%m-%d %H:%M")
            error_text = broadcast_ui.texts.get(
                "send_datetime_error", datetime_string=datetime_string
            )
            await broadcast_ui.open_send_datetime(error_text)

        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Confirmation Later Handlers
    # =========================================================================

    @staticmethod
    async def _confirmation_later_callback(
        call: CallbackQuery,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle callbacks in confirmation later state."""
        if call.data == "back":
            await broadcast_ui.open_send_datetime()
        elif call.data == "confirm":
            # Schedule broadcast
            await broadcast_ui.schedule_broadcast()
            # Return to broadcasts list
            await broadcast_ui.open_broadcasts_list()

        await call.answer()

    @staticmethod
    async def _confirmation_later_message(
        message: Message,
        broadcast_ui: BroadcastUIManager,
    ) -> None:
        """Handle messages in confirmation later state (delete them)."""
        await broadcast_ui.delete_user_message(message)

    # =========================================================================
    # Registration Methods
    # =========================================================================

    def register_on_router(self, router: Router) -> None:
        """
        Register all handlers on a router.

        Args:
            router: Router to register handlers on.
        """
        # Filter for private chats only
        router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)
        router.message.filter(F.chat.type == ChatType.PRIVATE)

        # Broadcasts list
        router.callback_query.register(
            self._broadcasts_list_callback,
            BroadcastUIState.broadcasts_list,
        )
        router.message.register(
            self._broadcasts_list_message,
            BroadcastUIState.broadcasts_list,
        )

        # Broadcast view
        router.callback_query.register(
            self._broadcast_view_callback,
            BroadcastUIState.broadcast_view,
        )
        router.message.register(
            self._broadcast_view_message,
            BroadcastUIState.broadcast_view,
        )

        # Broadcast delete
        router.callback_query.register(
            self._broadcast_delete_callback,
            BroadcastUIState.broadcast_delete,
        )
        router.message.register(
            self._broadcast_delete_message,
            BroadcastUIState.broadcast_delete,
        )

        # Send message
        router.callback_query.register(
            self._send_message_callback,
            BroadcastUIState.send_message,
        )
        router.message.register(
            self._send_message_message,
            BroadcastUIState.send_message,
        )

        # Send buttons
        router.callback_query.register(
            self._send_buttons_callback,
            BroadcastUIState.send_buttons,
        )
        router.message.register(
            self._send_buttons_message,
            BroadcastUIState.send_buttons,
        )

        # Message preview
        router.callback_query.register(
            self._message_preview_callback,
            BroadcastUIState.message_preview,
        )
        router.message.register(
            self._message_preview_message,
            BroadcastUIState.message_preview,
        )

        # Choose options
        router.callback_query.register(
            self._choose_options_callback,
            BroadcastUIState.choose_options,
        )
        router.message.register(
            self._choose_options_message,
            BroadcastUIState.choose_options,
        )

        # Confirmation now
        router.callback_query.register(
            self._confirmation_now_callback,
            BroadcastUIState.confirmation_now,
        )
        router.message.register(
            self._confirmation_now_message,
            BroadcastUIState.confirmation_now,
        )

        # Send datetime
        router.callback_query.register(
            self._send_datetime_callback,
            BroadcastUIState.send_datetime,
        )
        router.message.register(
            self._send_datetime_message,
            BroadcastUIState.send_datetime,
        )

        # Confirmation later
        router.callback_query.register(
            self._confirmation_later_callback,
            BroadcastUIState.confirmation_later,
        )
        router.message.register(
            self._confirmation_later_message,
            BroadcastUIState.confirmation_later,
        )

    def register(self, dp: Dispatcher) -> None:
        """
        Register all handlers on the dispatcher.

        Creates a new router, registers handlers, and includes it.

        Args:
            dp: Dispatcher to register handlers on.
        """
        router = Router(name="broadcast_ui")
        self.register_on_router(router)
        dp.include_router(router)
