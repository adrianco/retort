"""Payload validation for book resources.

Validation is deliberately kept free of Flask and SQLite imports so it can be
unit-tested on its own.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

MAX_TEXT_LENGTH = 500
MIN_YEAR = 1000

#: ISBN-10 (last character may be the check digit "X") or ISBN-13, once
#: separators have been stripped. Only the shape is checked, not the checksum.
_ISBN_RE = re.compile(r"\d{9}[\dX]|\d{13}")
_ISBN_SEPARATORS_RE = re.compile(r"[\s-]")

_MISSING = object()


class ValidationError(Exception):
    """Raised when a payload cannot be turned into a valid book.

    ``errors`` maps a field name to a human readable explanation.
    """

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Validation failed")
        self.errors = errors


def _max_year() -> int:
    # Books are routinely announced ahead of publication, so allow next year.
    return datetime.now(timezone.utc).year + 1


def _validate_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"'{field}' must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"'{field}' must not be empty")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise ValueError(f"'{field}' must be at most {MAX_TEXT_LENGTH} characters")
    return cleaned


def _validate_year(value: Any) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int; True would silently become the year 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("'year' must be an integer or null")
    if not MIN_YEAR <= value <= _max_year():
        raise ValueError(f"'year' must be between {MIN_YEAR} and {_max_year()}")
    return value


def _validate_isbn(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("'isbn' must be a string or null")
    if not value.strip():
        # An explicit empty string means "no ISBN" rather than an invalid one.
        return None
    normalised = _ISBN_SEPARATORS_RE.sub("", value).upper()
    if not _ISBN_RE.fullmatch(normalised):
        raise ValueError("'isbn' must be a valid ISBN-10 or ISBN-13")
    return normalised


_VALIDATORS = {
    "title": lambda value: _validate_text(value, "title"),
    "author": lambda value: _validate_text(value, "author"),
    "year": _validate_year,
    "isbn": _validate_isbn,
}

REQUIRED_FIELDS = ("title", "author")
OPTIONAL_FIELDS = ("year", "isbn")


def validate_book(payload: Any) -> dict[str, Any]:
    """Validate a create/replace payload and return the cleaned book fields.

    ``title`` and ``author`` are required; ``year`` and ``isbn`` default to
    ``None`` when omitted. Unknown fields are rejected so that typos such as
    ``{"tittle": ...}`` surface instead of being silently dropped.

    Raises:
        ValidationError: if any field is missing, unknown or malformed.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "Request body must be a JSON object"})

    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}

    for field in (*REQUIRED_FIELDS, *OPTIONAL_FIELDS):
        value = payload.get(field, _MISSING)
        if value is _MISSING:
            if field in REQUIRED_FIELDS:
                errors[field] = f"'{field}' is required"
            else:
                cleaned[field] = None
            continue
        try:
            cleaned[field] = _VALIDATORS[field](value)
        except ValueError as exc:
            errors[field] = str(exc)

    unknown = sorted(set(payload) - set(_VALIDATORS))
    for field in unknown:
        errors[field] = f"'{field}' is not a recognised field"

    if errors:
        raise ValidationError(errors)
    return cleaned
