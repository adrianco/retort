"""Validation and normalisation of book payloads received from clients."""

from __future__ import annotations

import unicodedata
from typing import Any, Callable

from .models import BookInput

MAX_TITLE_LENGTH = 255
MAX_AUTHOR_LENGTH = 255
MAX_ISBN_LENGTH = 32
MIN_YEAR = 1
MAX_YEAR = 9999


class ValidationError(ValueError):
    """A payload failed validation.

    ``errors`` maps every offending field name to a human-readable message.
    """

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def validate_book(payload: Any) -> BookInput:
    """Validate a decoded JSON payload and return the cleaned book fields.

    ``title`` and ``author`` are required. ``year`` and ``isbn`` are optional: an
    absent, ``null`` or (for ``isbn``) blank value is stored as ``None``. Unknown
    keys, such as an ``id`` echoed back by a client, are ignored. Every problem is
    reported at once rather than only the first.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "body must be a JSON object"})

    cleaned: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, parse in _FIELD_PARSERS.items():
        try:
            cleaned[name] = parse(payload.get(name))
        except ValueError as exc:
            errors[name] = f"{name} {exc}"
    if errors:
        raise ValidationError(errors)
    return BookInput(**cleaned)


def _required_text(value: Any, max_length: int) -> str:
    text = _optional_text(value, max_length)
    if text is None:
        raise ValueError("is required")
    return text


def _optional_text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("must be a string")
    text = value.strip()
    if _is_invisible(text):
        return None
    if len(text) > max_length:
        raise ValueError(f"must be at most {max_length} characters")
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise ValueError("must not contain control characters")
    try:
        # JSON permits lone surrogates ("\ud800"), which can be neither stored nor
        # sent back as UTF-8.
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("must be valid Unicode text") from None
    return text


def _is_invisible(text: str) -> bool:
    """True if there is nothing to see: empty, or only spaces and zero-width characters."""
    return all(char.isspace() or unicodedata.category(char) == "Cf" for char in text)


def _optional_year(value: Any) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, but ``true`` is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("must be an integer")
    if not MIN_YEAR <= value <= MAX_YEAR:
        raise ValueError(f"must be between {MIN_YEAR} and {MAX_YEAR}")
    return value


_FIELD_PARSERS: dict[str, Callable[[Any], Any]] = {
    "title": lambda value: _required_text(value, MAX_TITLE_LENGTH),
    "author": lambda value: _required_text(value, MAX_AUTHOR_LENGTH),
    "year": _optional_year,
    "isbn": lambda value: _optional_text(value, MAX_ISBN_LENGTH),
}
