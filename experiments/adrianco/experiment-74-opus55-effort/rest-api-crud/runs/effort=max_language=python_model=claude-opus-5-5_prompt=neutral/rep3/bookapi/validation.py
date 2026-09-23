"""Validation and normalisation of the book payloads clients send."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from functools import partial
from typing import Any

MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 255
MAX_ISBN_LENGTH = 32
MIN_YEAR = 1


class ValidationError(Exception):
    """A payload failed validation; ``errors`` maps each bad field to a message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(errors.values()))
        self.errors = errors


class _Invalid(Exception):
    """Raised by a field check; the message is completed with the field name."""


def validate_book(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the clean ``title``, ``author``, ``year`` and ``isbn`` of *payload*.

    ``title`` and ``author`` are required; ``year`` and ``isbn`` default to
    ``None``. Strings are stripped of surrounding whitespace and keys other than
    the four book fields are ignored. Every invalid field is reported at once
    through a single :class:`ValidationError`.
    """
    book: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for field, check in _FIELD_CHECKS.items():
        try:
            book[field] = check(payload.get(field))
        except _Invalid as exc:
            errors[field] = f"{field} {exc}"
    if errors:
        raise ValidationError(errors)
    return book


def latest_valid_year() -> int:
    """Next year, so forthcoming books can be catalogued before publication."""
    return datetime.date.today().year + 1


def _text(value: Any, *, required: bool, max_length: int) -> str | None:
    if value is None:
        if required:
            raise _Invalid("is required")
        return None
    if not isinstance(value, str):
        raise _Invalid("must be a string")
    value = value.strip()
    if not value:
        if required:
            raise _Invalid("must not be blank")
        return None
    if len(value) > max_length:
        raise _Invalid(f"must be at most {max_length} characters")
    return value


def _year(value: Any) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, but true/false is never a meaningful year.
    if isinstance(value, bool) or not isinstance(value, int):
        raise _Invalid("must be an integer")
    latest = latest_valid_year()
    if not MIN_YEAR <= value <= latest:
        raise _Invalid(f"must be between {MIN_YEAR} and {latest}")
    return value


_FIELD_CHECKS = {
    "title": partial(_text, required=True, max_length=MAX_TITLE_LENGTH),
    "author": partial(_text, required=True, max_length=MAX_AUTHOR_LENGTH),
    "year": _year,
    "isbn": partial(_text, required=False, max_length=MAX_ISBN_LENGTH),
}
