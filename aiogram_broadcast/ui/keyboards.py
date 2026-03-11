"""Inline keyboards for broadcast UI."""

from dataclasses import dataclass
from typing import ClassVar

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


@dataclass
class BroadcastUIKeyboards:
    """
    Inline keyboards for broadcast UI navigation.

    Supports multiple languages with automatic fallback to English.

    Usage:
        keyboards = BroadcastUIKeyboards("ru")
        markup = keyboards.back()
    """

    button_texts: ClassVar[dict[str, dict[str, str]]] = {
        "en": {
            "add": "Add",
            "delete": "Delete",
            "back": "Back",
            "skip": "Skip",
            "next": "Next",
            "later": "Later",
            "now": "Now",
            "confirm": "Confirm",
            "cancel": "Cancel",
        },
        "ru": {
            "add": "Добавить",
            "delete": "Удалить",
            "back": "Назад",
            "skip": "Пропустить",
            "next": "Далее",
            "later": "Позже",
            "now": "Сейчас",
            "confirm": "Подтвердить",
            "cancel": "Отмена",
        },
    }

    language_code: str = "en"

    def __init__(self, language_code: str | None = None) -> None:
        """
        Initialize keyboards with language code.

        Args:
            language_code: Language code (e.g., "en", "ru").
                          Falls back to "en" if not supported.
        """
        if language_code and language_code in self.button_texts:
            self.language_code = language_code
        else:
            self.language_code = "en"

    def _get_button_text(self, key: str) -> str:
        """Get localized button text."""
        return self.button_texts.get(self.language_code, {}).get(
            key, self.button_texts["en"].get(key, key)
        )

    def _button(self, key: str, callback_data: str | None = None) -> InlineKeyboardButton:
        """Create a button with localized text."""
        return InlineKeyboardButton(
            text=self._get_button_text(key),
            callback_data=callback_data or key,
        )

    def _url_button(self, text: str, url: str) -> InlineKeyboardButton:
        """Create a URL button."""
        return InlineKeyboardButton(text=text, url=url)

    def back(self) -> InlineKeyboardMarkup:
        """Back button only."""
        return InlineKeyboardMarkup(inline_keyboard=[[self._button("back")]])

    def back_add(self) -> InlineKeyboardMarkup:
        """Back and Add buttons."""
        return InlineKeyboardMarkup(
            inline_keyboard=[[self._button("back"), self._button("add")]]
        )

    def back_next(self) -> InlineKeyboardMarkup:
        """Back and Next buttons."""
        return InlineKeyboardMarkup(
            inline_keyboard=[[self._button("back"), self._button("next")]]
        )

    def back_delete(self) -> InlineKeyboardMarkup:
        """Back and Delete buttons."""
        return InlineKeyboardMarkup(
            inline_keyboard=[[self._button("back"), self._button("delete")]]
        )

    def back_confirm(self) -> InlineKeyboardMarkup:
        """Back and Confirm buttons."""
        return InlineKeyboardMarkup(
            inline_keyboard=[[self._button("back"), self._button("confirm")]]
        )

    def back_skip(self) -> InlineKeyboardMarkup:
        """Back and Skip buttons."""
        return InlineKeyboardMarkup(
            inline_keyboard=[[self._button("back"), self._button("skip")]]
        )

    def send_options(self) -> InlineKeyboardMarkup:
        """Send now/later options."""
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [self._button("now"), self._button("later")],
                [self._button("back")],
            ]
        )

    def broadcasts_list(
        self,
        items: list[tuple[str, str]],
        current_page: int,
        total_pages: int,
    ) -> InlineKeyboardMarkup:
        """
        Build paginated list of scheduled broadcasts.

        Args:
            items: List of (display_text, callback_data) tuples.
            current_page: Current page number (1-indexed).
            total_pages: Total number of pages.

        Returns:
            InlineKeyboardMarkup with items, pagination, and action buttons.
        """
        paginator = InlineKeyboardPaginator(
            items=items,
            current_page=current_page,
            total_pages=total_pages,
            after_reply_markup=self.back_add(),
        )
        return paginator.as_markup()

    @staticmethod
    def build_url_buttons(buttons_text: str) -> InlineKeyboardMarkup | None:
        """
        Build inline URL buttons from text input.

        Format:
            Button text | url
            Button1 | url1, Button2 | url2  (same row)
            Button1 | url1
            Button2 | url2                   (different rows)

        Args:
            buttons_text: Raw text with button definitions.

        Returns:
            InlineKeyboardMarkup or None if parsing fails.
        """
        if not buttons_text or not buttons_text.strip():
            return None

        try:
            rows = [row.strip() for row in buttons_text.strip().split("\n") if row.strip()]
            keyboard = []

            for row in rows:
                row_buttons = []
                button_defs = [b.strip() for b in row.split(",") if b.strip()]

                for button_def in button_defs:
                    parts = button_def.split("|")
                    if len(parts) != 2:
                        return None

                    text = parts[0].strip()
                    url = parts[1].strip()

                    if not text or not url:
                        return None

                    # Basic URL validation
                    if not (url.startswith("http://") or url.startswith("https://")):
                        if url.startswith("www."):
                            url = "https://" + url
                        else:
                            return None

                    row_buttons.append(InlineKeyboardButton(text=text, url=url))

                if row_buttons:
                    keyboard.append(row_buttons)

            return InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

        except Exception:
            return None


class InlineKeyboardPaginator:
    """
    Paginator for inline keyboard lists.

    Creates navigation buttons for multi-page lists with
    first/prev/current/next/last page buttons.
    """

    first_page_label = "« {}"
    previous_page_label = "‹ {}"
    current_page_label = "· {} ·"
    next_page_label = "{} ›"
    last_page_label = "{} »"

    def __init__(
        self,
        items: list[tuple[str, str]],
        current_page: int = 1,
        total_pages: int = 1,
        row_width: int = 1,
        data_pattern: str = "page:{}",
        before_reply_markup: InlineKeyboardMarkup | None = None,
        after_reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        """
        Initialize paginator.

        Args:
            items: List of (display_text, callback_data) tuples.
            current_page: Current page number (1-indexed).
            total_pages: Total number of pages.
            row_width: Number of items per row.
            data_pattern: Pattern for page navigation callback data.
            before_reply_markup: Markup to add before items.
            after_reply_markup: Markup to add after items.
        """
        self.items = items
        self.current_page = current_page
        self.total_pages = total_pages
        self.row_width = row_width
        self.data_pattern = data_pattern
        self.builder = InlineKeyboardBuilder()
        self.before_reply_markup = before_reply_markup
        self.after_reply_markup = after_reply_markup

    def _items_builder(self) -> InlineKeyboardBuilder:
        """Build items keyboard."""
        builder = InlineKeyboardBuilder()
        for text, callback_data in self.items:
            builder.button(text=text, callback_data=callback_data)
        builder.adjust(self.row_width)
        return builder

    def _navigation_builder(self) -> InlineKeyboardBuilder:
        """Build navigation keyboard."""
        builder = InlineKeyboardBuilder()
        keyboard_dict: dict[int, str] = {}

        if self.total_pages > 1:
            if self.total_pages <= 5:
                for page in range(1, self.total_pages + 1):
                    keyboard_dict[page] = str(page)
            else:
                if self.current_page <= 3:
                    page_range = range(1, 4)
                    keyboard_dict[4] = self.next_page_label.format(4)
                    keyboard_dict[self.total_pages] = self.last_page_label.format(
                        self.total_pages
                    )
                elif self.current_page > self.total_pages - 3:
                    keyboard_dict[1] = self.first_page_label.format(1)
                    keyboard_dict[self.total_pages - 3] = self.previous_page_label.format(
                        self.total_pages - 3
                    )
                    page_range = range(self.total_pages - 2, self.total_pages + 1)
                else:
                    keyboard_dict[1] = self.first_page_label.format(1)
                    keyboard_dict[self.current_page - 1] = self.previous_page_label.format(
                        self.current_page - 1
                    )
                    keyboard_dict[self.current_page + 1] = self.next_page_label.format(
                        self.current_page + 1
                    )
                    keyboard_dict[self.total_pages] = self.last_page_label.format(
                        self.total_pages
                    )
                    page_range = [self.current_page]

                for page in page_range:
                    keyboard_dict[page] = str(page)

            keyboard_dict[self.current_page] = self.current_page_label.format(
                self.current_page
            )

            for key, val in sorted(keyboard_dict.items()):
                builder.button(text=val, callback_data=self.data_pattern.format(key))
            builder.adjust(5)

        return builder

    def as_markup(self) -> InlineKeyboardMarkup:
        """Build final markup with all components."""
        if self.before_reply_markup:
            self.builder.attach(
                InlineKeyboardBuilder(markup=self.before_reply_markup.inline_keyboard)
            )

        self.builder.attach(self._items_builder())
        self.builder.attach(self._navigation_builder())

        if self.after_reply_markup:
            self.builder.attach(
                InlineKeyboardBuilder(markup=self.after_reply_markup.inline_keyboard)
            )

        return self.builder.as_markup()
