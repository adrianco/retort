"""Validation and normalisation of book payloads.

Independent of HTTP and SQLite: takes a decoded JSON object and returns a
:class:`~bookapi.models.BookData`, or raises :class:`ValidationError` describing every
invalid field at once so a client can fix them in a single round trip.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable, Mapping
from functools import partial
from typing import Any

from .models import BookData

MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 255
MAX_ISBN_LENGTH = 32
MIN_YEAR = 1


class ValidationError(Exception):
    """Raised for an invalid payload; ``errors`` maps each bad field to a message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__(errors)
        self.errors = errors


def latest_year() -> int:
    """Latest accepted publication year: next calendar year, to allow announced titles."""
    return datetime.date.today().year + 1


def _text(name: str, value: Any, *, max_length: int, required: bool) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{name} is required")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    text = value.strip()
    if not text:
        if required:
            raise ValueError(f"{name} must not be blank")
        return None  # an optional field left blank is the same as omitting it
    if len(text) > max_length:
        raise ValueError(f"{name} must be at most {max_length} characters")
    try:
        text.encode("utf-8")  # rejects lone surrogates ("\ud800"), which cannot be stored
    except UnicodeEncodeError:
        raise ValueError(f"{name} must be valid Unicode text") from None
    return text


def _year(name: str, value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):  # bool is an int subclass
        raise ValueError(f"{name} must be an integer")
    latest = latest_year()
    if not MIN_YEAR <= value <= latest:
        raise ValueError(f"{name} must be between {MIN_YEAR} and {latest}")
    return value


# Field name -> checker(name, raw value) returning the cleaned value or raising ValueError.
_FIELDS: dict[str, Callable[[str, Any], Any]] = {
    "title": partial(_text, max_length=MAX_TITLE_LENGTH, required=True),
    "author": partial(_text, max_length=MAX_AUTHOR_LENGTH, required=True),
    "year": _year,
    "isbn": partial(_text, max_length=MAX_ISBN_LENGTH, required=False),
}


def validate_book(payload: Mapping[str, Any]) -> BookData:
    """Validate a decoded JSON object and return the normalised book data.

    Unknown keys (including a client-supplied ``id``) are ignored. Text is stripped of
    surrounding whitespace, and a blank optional field becomes ``None``.
    """
    cleaned: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, check in _FIELDS.items():
        try:
            cleaned[name] = check(name, payload.get(name))
        except ValueError as exc:
            errors[name] = str(exc)
    if errors:
        raise ValidationError(errors)
    return BookData(**cleaned)
