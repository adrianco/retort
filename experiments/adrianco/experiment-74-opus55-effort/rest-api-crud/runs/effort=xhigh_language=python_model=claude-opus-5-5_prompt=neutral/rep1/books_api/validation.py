"""Validation of book payloads received from clients.

Rules:

* ``title`` and ``author`` are required non-blank strings (surrounding
  whitespace is trimmed) of at most ``MAX_TEXT_LENGTH`` characters.
* ``year`` is optional; when given it must be an integer between ``MIN_YEAR``
  and next year (books can be listed shortly before publication).
* ``isbn`` is optional; when given it must look like an ISBN-10 or ISBN-13:
  10 or 13 digits (an ISBN-10 may end in ``X``), optionally separated by
  hyphens or spaces. A blank string is treated as "no ISBN". The value is
  stored as supplied (trimmed), so clients get back what they sent.
* Unknown fields are ignored.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import BookData

MAX_TEXT_LENGTH = 500
MIN_YEAR = -9999

# Digits (or X), with single hyphens/spaces allowed only between characters.
_ISBN_SHAPE = re.compile(r"[\dXx](?:[ \-]?[\dXx])*")
_ISBN10 = re.compile(r"\d{9}[\dX]")
_ISBN13 = re.compile(r"\d{13}")


class ValidationError(Exception):
    """Raised when a payload is invalid; ``errors`` maps field name to message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(f"{field}: {msg}" for field, msg in errors.items()))
        self.errors = errors


def max_year() -> int:
    return date.today().year + 1


def validate_book(payload: Any) -> BookData:
    """Validate a decoded JSON payload and return the cleaned book fields.

    All problems are collected so the client can fix them in one round trip.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    title = _required_text(payload, "title", errors)
    author = _required_text(payload, "author", errors)
    year = _optional_year(payload, errors)
    isbn = _optional_isbn(payload, errors)

    if errors:
        raise ValidationError(errors)
    # The helpers only return None for required fields after recording an error.
    assert title is not None and author is not None
    return BookData(title=title, author=author, year=year, isbn=isbn)


def _required_text(payload: dict[str, Any], field: str, errors: dict[str, str]) -> str | None:
    value = payload.get(field)
    if value is None:
        errors[field] = f"{field} is required"
        return None
    if not isinstance(value, str):
        errors[field] = f"{field} must be a string"
        return None
    value = value.strip()
    if not value:
        errors[field] = f"{field} must not be blank"
        return None
    if len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"{field} must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return value


def _optional_year(payload: dict[str, Any], errors: dict[str, str]) -> int | None:
    value = payload.get("year")
    if value is None:
        return None
    # bool is a subclass of int, but `true` is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "year must be an integer"
        return None
    upper = max_year()
    if not MIN_YEAR <= value <= upper:
        errors["year"] = f"year must be between {MIN_YEAR} and {upper}"
        return None
    return value


def _optional_isbn(payload: dict[str, Any], errors: dict[str, str]) -> str | None:
    value = payload.get("isbn")
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "isbn must be a string"
        return None
    value = value.strip()
    if not value:
        return None
    compact = re.sub(r"[ \-]", "", value).upper()
    if not (
        _ISBN_SHAPE.fullmatch(value)
        and (_ISBN10.fullmatch(compact) or _ISBN13.fullmatch(compact))
    ):
        errors["isbn"] = (
            "isbn must be an ISBN-10 or ISBN-13 "
            "(10 or 13 digits, optionally separated by hyphens or spaces)"
        )
        return None
    return value
