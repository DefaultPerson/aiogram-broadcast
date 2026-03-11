"""Tests for UI pure logic (texts, keyboards, utils)."""

from __future__ import annotations

from datetime import datetime

from aiogram_broadcast.ui.keyboards import BroadcastUIKeyboards
from aiogram_broadcast.ui.texts import BroadcastUITexts
from aiogram_broadcast.ui.utils import validate_datetime, validate_url


class TestTexts:
    def test_russian_returns_russian(self) -> None:
        texts = BroadcastUITexts("ru")
        result = texts.get("outdated_text")
        assert "устарело" in result

    def test_unsupported_falls_back_to_english(self) -> None:
        texts = BroadcastUITexts("zh")
        result = texts.get("outdated_text")
        assert "outdated" in result.lower()

    def test_format_kwargs(self) -> None:
        texts = BroadcastUITexts("en")
        result = texts.get("broadcasts_list", total="42")
        assert "42" in result

    def test_missing_key_returns_bracket(self) -> None:
        texts = BroadcastUITexts("en")
        assert texts.get("nonexistent_key_xyz") == "[nonexistent_key_xyz]"


class TestKeyboards:
    def test_build_url_buttons_valid(self) -> None:
        markup = BroadcastUIKeyboards.build_url_buttons("Click | https://example.com")
        assert markup is not None
        assert len(markup.inline_keyboard) == 1
        assert markup.inline_keyboard[0][0].url == "https://example.com"

    def test_build_url_buttons_multirow(self) -> None:
        text = "Row1 | https://a.com\nRow2 | https://b.com"
        markup = BroadcastUIKeyboards.build_url_buttons(text)
        assert markup is not None
        assert len(markup.inline_keyboard) == 2

    def test_build_url_buttons_invalid(self) -> None:
        assert BroadcastUIKeyboards.build_url_buttons("no pipe here") is None

    def test_build_url_buttons_www_prefix(self) -> None:
        markup = BroadcastUIKeyboards.build_url_buttons("Site | www.example.com")
        assert markup is not None
        assert markup.inline_keyboard[0][0].url == "https://www.example.com"


class TestUtils:
    def test_validate_datetime_valid(self) -> None:
        result = validate_datetime("2024-06-01 12:30")
        assert isinstance(result, datetime)
        assert result.hour == 12
        assert result.minute == 30

    def test_validate_datetime_invalid(self) -> None:
        assert validate_datetime("not-a-date") is None
        assert validate_datetime("06/01/2024 12:00") is None

    def test_validate_url_valid(self) -> None:
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://example.com/path") is not None

    def test_validate_url_invalid(self) -> None:
        assert validate_url("not a url") is None
