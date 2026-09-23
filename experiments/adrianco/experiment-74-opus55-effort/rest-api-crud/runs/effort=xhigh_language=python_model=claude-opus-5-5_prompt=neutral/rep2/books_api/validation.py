"""Validation and normalisation of client-supplied book payloads."""

from __future__ import annotations

import datetime
import re
from typing import Any, Callable

FIELDS = ("title", "author", "year", "isbn")
REQUIRED_FIELDS = ("title", "author")

MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 300
MIN_YEAR = -9999

# ISBN-10 / ISBN-13 shape (the check digit is not verified). Single hyphens or
# spaces are allowed between digits, e.g. "978-0-452-28423-4" or "0 452 28423 8".
_ISBN10 = re.compile(r"(?:[0-9][- ]?){9}[0-9Xx]")
_ISBN13 = re.compile(r"(?:[0-9][- ]?){12}[0-9]")


class ValidationError(Exception):
    """Raised when a payload is invalid. ``errors`` maps a field name to a message."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{field}: {msg}" for field, msg in errors.items()))
        self.errors = errors


def _clean_text(value: Any, name: str, max_length: int) -> str:
    if value is None:
        raise ValueError(f"{name} is required")
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    if len(value) > max_length:
        raise ValueError(f"{name} must be at most {max_length} characters")
    return value


def _clean_year(value: Any) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, but `"year": true` is clearly a client error.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("year must be an integer")
    max_year = datetime.date.today().year
    if not MIN_YEAR <= value <= max_year:
        raise ValueError(f"year must be between {MIN_YEAR} and {max_year}")
    return value


def _clean_isbn(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("isbn must be a string")
    value = value.strip()
    if not value:
        return None
    if not (_ISBN10.fullmatch(value) or _ISBN13.fullmatch(value)):
        raise ValueError("isbn must be a 10 or 13 digit ISBN (hyphens or spaces allowed)")
    return value


_CLEANERS: dict[str, Callable[[Any], Any]] = {
    "title": lambda value: _clean_text(value, "title", MAX_TITLE_LENGTH),
    "author": lambda value: _clean_text(value, "author", MAX_AUTHOR_LENGTH),
    "year": _clean_year,
    "isbn": _clean_isbn,
}


def validate_book(payload: Any, *, partial: bool = False) -> dict[str, Any]:
    """Return a cleaned dict holding only the known book fields present in ``payload``.

    With ``partial=False`` (creating a book) ``title`` and ``author`` are required.
    With ``partial=True`` (updating a book) every field is optional, but at least
    one must be supplied, and ``title``/``author`` still cannot be null or blank.
    ``year`` and ``isbn`` may be null to clear them. Unknown keys are ignored.

    Raises ``ValidationError`` listing every problem found, not just the first.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "request body must be a JSON object"})

    clean: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, cleaner in _CLEANERS.items():
        if name not in payload:
            if not partial and name in REQUIRED_FIELDS:
                errors[name] = f"{name} is required"
            continue
        try:
            clean[name] = cleaner(payload[name])
        except ValueError as exc:
            errors[name] = str(exc)

    if partial and not clean and not errors:
        errors["body"] = f"provide at least one of: {', '.join(FIELDS)}"
    if errors:
        raise ValidationError(errors)
    return clean
