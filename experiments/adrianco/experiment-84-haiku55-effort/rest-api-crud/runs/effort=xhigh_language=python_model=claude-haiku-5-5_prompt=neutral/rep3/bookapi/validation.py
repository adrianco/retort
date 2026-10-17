"""Input validation for book payloads."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import BookFields

MAX_TEXT_LENGTH = 500
# The oldest surviving written records date from around 3000 BCE.
MIN_YEAR = -3000

_ISBN10_RE = re.compile(r"[0-9]{9}[0-9X]")
_ISBN13_RE = re.compile(r"[0-9]{13}")


class ValidationError(Exception):
    """A payload failed validation. ``errors`` maps each field name to a message."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload: Any) -> BookFields:
    """Check a decoded JSON payload and return the cleaned book fields.

    Every problem is collected before raising, so a client can fix them all at once.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    title = _required_text(payload, "title", errors)
    author = _required_text(payload, "author", errors)
    year = _optional_year(payload.get("year"), errors)
    isbn = _optional_isbn(payload.get("isbn"), errors)

    if errors:
        raise ValidationError(errors)
    return BookFields(title=title, author=author, year=year, isbn=isbn)


def normalize_isbn(raw: str) -> str | None:
    """Return the ISBN as bare digits (an ISBN-10 may end in X), or None if invalid.

    Hyphens and spaces are allowed in ``raw`` and removed.
    """
    isbn = re.sub(r"[\s-]", "", raw).upper()
    if _ISBN10_RE.fullmatch(isbn):
        return isbn if _isbn10_checksum_ok(isbn) else None
    if _ISBN13_RE.fullmatch(isbn):
        return isbn if _isbn13_checksum_ok(isbn) else None
    return None


def _required_text(payload: dict[str, Any], field: str, errors: dict[str, str]) -> str:
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
        return ""
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return ""
    text = value.strip()
    if not text:
        errors[field] = "must not be blank"
    elif len(text) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
    return text


def _optional_year(value: Any, errors: dict[str, str]) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int in Python, but JSON true/false is never a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
        return None
    max_year = date.today().year + 1  # allow books announced for next year
    if not MIN_YEAR <= value <= max_year:
        errors["year"] = f"must be between {MIN_YEAR} and {max_year}"
        return None
    return value


def _optional_isbn(value: Any, errors: dict[str, str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    isbn = normalize_isbn(value)
    if isbn is None:
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
    return isbn


def _isbn10_checksum_ok(isbn: str) -> bool:
    total = sum((10 - i) * int(digit) for i, digit in enumerate(isbn[:9]))
    check = 10 if isbn[9] == "X" else int(isbn[9])
    return (total + check) % 11 == 0


def _isbn13_checksum_ok(isbn: str) -> bool:
    total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(isbn[:12]))
    return (10 - total % 10) % 10 == int(isbn[12])
