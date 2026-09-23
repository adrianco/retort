"""Validation and normalisation of incoming book payloads."""

from __future__ import annotations

import datetime
import re
from typing import Any, TypedDict

FIELDS = ("title", "author", "year", "isbn")
# Accepted in request bodies (so a GET response can be PUT back as-is) but ignored.
READ_ONLY_FIELDS = frozenset({"id"})

MAX_TEXT_LENGTH = 500
MIN_YEAR = 1
# 13 digits plus up to four separators, e.g. "978-0-13-468599-1".
MAX_ISBN_LENGTH = 17

_ISBN_SEPARATORS = re.compile(r"[- ]")
_ISBN_10 = re.compile(r"[0-9]{9}[0-9X]")
_ISBN_13 = re.compile(r"[0-9]{13}")


class BookFields(TypedDict):
    """The writable fields of a book, as stored in the database."""

    title: str
    author: str
    year: int | None
    isbn: str | None


class ValidationError(ValueError):
    """Raised when a payload is not a valid book.

    ``errors`` maps each offending field to a human-readable message.
    """

    def __init__(self, message: str, errors: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or {}


def validate_book(payload: Any, *, current_year: int | None = None) -> BookFields:
    """Validate a decoded JSON payload and return the cleaned book fields.

    ``title`` and ``author`` are required non-blank strings. ``year`` and
    ``isbn`` are optional; when omitted (or null) they are stored as null.
    Unknown fields are rejected so that typos such as ``"autor"`` do not
    silently lose data.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")

    if current_year is None:
        current_year = datetime.date.today().year

    errors: dict[str, str] = {}
    for key in payload:
        if key not in FIELDS and key not in READ_ONLY_FIELDS:
            errors[key] = f"unknown field; allowed fields are: {', '.join(FIELDS)}"

    title = _required_text(payload, "title", errors)
    author = _required_text(payload, "author", errors)
    year = _optional_year(payload.get("year"), current_year, errors)
    isbn = _optional_isbn(payload.get("isbn"), errors)

    if errors:
        raise ValidationError("Validation failed", errors)
    return BookFields(title=title, author=author, year=year, isbn=isbn)


def _required_text(payload: dict[str, Any], field: str, errors: dict[str, str]) -> str:
    value = payload.get(field)
    if value is None:
        errors[field] = f"{field} is required"
        return ""
    if not isinstance(value, str):
        errors[field] = f"{field} must be a string"
        return ""
    value = value.strip()
    if not value:
        errors[field] = f"{field} must not be blank"
    elif len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"{field} must be at most {MAX_TEXT_LENGTH} characters"
    return value


def _optional_year(value: Any, current_year: int, errors: dict[str, str]) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, but `true` is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "year must be an integer"
        return None
    if not MIN_YEAR <= value <= current_year:
        errors["year"] = f"year must be between {MIN_YEAR} and {current_year}"
    return value


def _optional_isbn(value: Any, errors: dict[str, str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "isbn must be a string"
        return None
    value = value.strip()
    if not value:
        return None
    compact = _ISBN_SEPARATORS.sub("", value).upper()
    if len(value) > MAX_ISBN_LENGTH or not (
        _ISBN_10.fullmatch(compact) or _ISBN_13.fullmatch(compact)
    ):
        errors["isbn"] = (
            "isbn must be an ISBN-10 or ISBN-13: 10 or 13 digits "
            "(ISBN-10 may end in X), optionally separated by hyphens or spaces"
        )
    return value
