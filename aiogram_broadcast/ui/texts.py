"""Localized text messages for broadcast UI."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class BroadcastUITexts:
    """
    Localized text messages for broadcast UI.

    Supports multiple languages with automatic fallback to English.

    Usage:
        texts = BroadcastUITexts("ru")
        message = texts.get("broadcasts_list")
    """

    text_messages: ClassVar[dict[str, dict[str, str]]] = {
        "en": {
            "outdated_text": "This message is outdated...",
            "broadcasts_list": (
                "<b>Broadcast Menu</b>\n\n"
                "<b>Add</b> - create a new broadcast\n\n"
                "Total subscribers: <b>{total}</b>\n\n"
                "Scheduled broadcasts:"
            ),
            "broadcast_view": (
                "The message above is an example of a scheduled broadcast.\n\n"
                "<b>Delete</b> - cancel this scheduled broadcast\n\n"
                "Choose an action:"
            ),
            "broadcast_delete": "Are you sure you want to delete this scheduled broadcast?",
            "send_message": (
                "<b>Send your broadcast message</b>\n\n"
                "You can send:\n"
                "- Text message\n"
                "- Photo with caption\n"
                "- Video with caption\n"
                "- Document with caption\n"
                "- Or forward any message"
            ),
            "send_buttons": (
                "<b>Add inline buttons</b>\n\n"
                "Send button text and link(s) in the format:\n"
                "<code>Button text | link</code>\n\n"
                "Example:\n"
                "<code>Visit Website | https://example.com</code>\n\n"
                "Multiple buttons in a row (comma-separated):\n"
                "<code>First | https://url1.com, Second | https://url2.com</code>\n\n"
                "Multiple rows (new lines):\n"
                "<code>Row 1 Button | https://url1.com\n"
                "Row 2 Button | https://url2.com</code>\n\n"
                "Press <b>Skip</b> to send without buttons."
            ),
            "send_buttons_error": (
                "<b>Error parsing buttons</b>\n\n"
                "Please check the format:\n"
                "<code>Button text | link</code>\n\n"
                "Make sure all links are valid URLs."
            ),
            "message_preview": (
                "The message above is how your broadcast will look.\n\n"
                "<b>Next</b> - continue to send options\n\n"
                "Choose an action:"
            ),
            "choose_options": (
                "<b>When to send?</b>\n\n"
                "<b>Now</b> - send immediately\n"
                "<b>Later</b> - schedule for later"
            ),
            "confirmation_now": (
                "<b>Confirm broadcast</b>\n\n"
                "Are you sure you want to send this broadcast to all subscribers now?"
            ),
            "send_datetime": (
                "<b>Schedule broadcast</b>\n\n"
                "Send the date and time in format:\n"
                "<code>YYYY-MM-DD HH:MM</code>\n\n"
                "Example:\n"
                "<code>{datetime_string}</code>"
            ),
            "send_datetime_error": (
                "<b>Invalid date format</b>\n\n"
                "Please use format:\n"
                "<code>YYYY-MM-DD HH:MM</code>\n\n"
                "Example:\n"
                "<code>{datetime_string}</code>"
            ),
            "confirmation_later": (
                "<b>Confirm scheduled broadcast</b>\n\n"
                "Are you sure you want to schedule this broadcast?"
            ),
            "broadcast_started": (
                "Broadcast started. You will be notified when it completes."
            ),
            "broadcast_completed": (
                "<b>Broadcast completed</b>\n\n"
                "Total: <b>{total}</b>\n"
                "Successful: <b>{successful}</b>\n"
                "Failed: <b>{failed}</b>"
            ),
            "no_scheduled_broadcasts": "No scheduled broadcasts.",
        },
        "ru": {
            "outdated_text": "Это сообщение устарело...",
            "broadcasts_list": (
                "<b>Меню рассылки</b>\n\n"
                "<b>Добавить</b> - создать новую рассылку\n\n"
                "Всего подписчиков: <b>{total}</b>\n\n"
                "Запланированные рассылки:"
            ),
            "broadcast_view": (
                "Сообщение выше - пример запланированной рассылки.\n\n"
                "<b>Удалить</b> - отменить эту рассылку\n\n"
                "Выберите действие:"
            ),
            "broadcast_delete": "Вы уверены, что хотите удалить эту запланированную рассылку?",
            "send_message": (
                "<b>Отправьте сообщение для рассылки</b>\n\n"
                "Вы можете отправить:\n"
                "- Текстовое сообщение\n"
                "- Фото с подписью\n"
                "- Видео с подписью\n"
                "- Документ с подписью\n"
                "- Или переслать любое сообщение"
            ),
            "send_buttons": (
                "<b>Добавить инлайн кнопки</b>\n\n"
                "Отправьте текст кнопок и ссылки в формате:\n"
                "<code>Текст кнопки | ссылка</code>\n\n"
                "Пример:\n"
                "<code>Перейти на сайт | https://example.com</code>\n\n"
                "Несколько кнопок в ряд (через запятую):\n"
                "<code>Первая | https://url1.com, Вторая | https://url2.com</code>\n\n"
                "Несколько рядов (новые строки):\n"
                "<code>Кнопка ряд 1 | https://url1.com\n"
                "Кнопка ряд 2 | https://url2.com</code>\n\n"
                "Нажмите <b>Пропустить</b> чтобы отправить без кнопок."
            ),
            "send_buttons_error": (
                "<b>Ошибка парсинга кнопок</b>\n\n"
                "Проверьте формат:\n"
                "<code>Текст кнопки | ссылка</code>\n\n"
                "Убедитесь, что все ссылки корректные."
            ),
            "message_preview": (
                "Сообщение выше - так будет выглядеть ваша рассылка.\n\n"
                "<b>Далее</b> - перейти к выбору времени\n\n"
                "Выберите действие:"
            ),
            "choose_options": (
                "<b>Когда отправить?</b>\n\n"
                "<b>Сейчас</b> - отправить немедленно\n"
                "<b>Позже</b> - запланировать на потом"
            ),
            "confirmation_now": (
                "<b>Подтверждение рассылки</b>\n\n"
                "Вы уверены, что хотите отправить рассылку всем подписчикам сейчас?"
            ),
            "send_datetime": (
                "<b>Запланировать рассылку</b>\n\n"
                "Отправьте дату и время в формате:\n"
                "<code>YYYY-MM-DD HH:MM</code>\n\n"
                "Пример:\n"
                "<code>{datetime_string}</code>"
            ),
            "send_datetime_error": (
                "<b>Неверный формат даты</b>\n\n"
                "Используйте формат:\n"
                "<code>YYYY-MM-DD HH:MM</code>\n\n"
                "Пример:\n"
                "<code>{datetime_string}</code>"
            ),
            "confirmation_later": (
                "<b>Подтверждение отложенной рассылки</b>\n\n"
                "Вы уверены, что хотите запланировать эту рассылку?"
            ),
            "broadcast_started": (
                "Рассылка запущена. Вы получите уведомление о завершении."
            ),
            "broadcast_completed": (
                "<b>Рассылка завершена</b>\n\n"
                "Всего: <b>{total}</b>\n"
                "Успешно: <b>{successful}</b>\n"
                "Ошибок: <b>{failed}</b>"
            ),
            "no_scheduled_broadcasts": "Нет запланированных рассылок.",
        },
    }

    language_code: str = "en"

    def __init__(self, language_code: str | None = None) -> None:
        """
        Initialize texts with language code.

        Args:
            language_code: Language code (e.g., "en", "ru").
                          Falls back to "en" if not supported.
        """
        if language_code and language_code in self.text_messages:
            self.language_code = language_code
        else:
            self.language_code = "en"

    def get(self, key: str, **kwargs: str) -> str:
        """
        Get localized text by key.

        Args:
            key: Text message key.
            **kwargs: Format arguments.

        Returns:
            Localized text message.
        """
        text = self.text_messages.get(self.language_code, {}).get(key, "")
        if not text:
            text = self.text_messages["en"].get(key, f"[{key}]")
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        return text
