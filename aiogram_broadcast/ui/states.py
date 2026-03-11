"""FSM states for broadcast UI menu."""

from aiogram.fsm.state import State, StatesGroup


class BroadcastUIState(StatesGroup):
    """States for broadcast UI navigation."""

    # Main menu with list of scheduled broadcasts
    broadcasts_list = State()

    # Single broadcast view
    broadcast_view = State()

    # Confirm delete scheduled broadcast
    broadcast_delete = State()

    # Waiting for message content (text, photo, video, document, etc.)
    send_message = State()

    # Waiting for inline buttons input
    send_buttons = State()

    # Preview message before sending
    message_preview = State()

    # Choose send options (now/later)
    choose_options = State()

    # Confirm immediate send
    confirmation_now = State()

    # Waiting for scheduled datetime input
    send_datetime = State()

    # Confirm scheduled send
    confirmation_later = State()
