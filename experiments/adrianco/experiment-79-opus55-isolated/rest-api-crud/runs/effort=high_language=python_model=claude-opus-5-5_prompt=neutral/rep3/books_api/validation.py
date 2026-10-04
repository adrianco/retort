"""Validation of book payloads received from clients."""

from __future__ import annotations

from typing import Any

MAX_TEXT_LENGTH = 500
MAX_ISBN_LENGTH = 32
MIN_YEAR = 1
MAX_YEAR = 9999


class ValidationError(Exception):
    """Raised when a payload is invalid; ``errors`` maps field name to message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Validation failed")
        self.errors = errors


def validate_book(payload: Any) -> dict[str, Any]:
    """Return the cleaned ``title``, ``author``, ``year`` and ``isbn`` fields.

    ``title`` and ``author`` are required non-blank strings. ``year`` and
    ``isbn`` are optional and become ``None`` when omitted. Unknown keys are
    ignored. All problems are collected and reported together.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    book: dict[str, Any] = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if value is None:
            errors[field] = "is required"
        elif not isinstance(value, str):
            errors[field] = "must be a string"
        elif not value.strip():
            errors[field] = "must not be blank"
        elif len(value.strip()) > MAX_TEXT_LENGTH:
            errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
        else:
            book[field] = value.strip()

    year = payload.get("year")
    # bool is a subclass of int, but true/false is not a year.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    elif year is not None and not MIN_YEAR <= year <= MAX_YEAR:
        errors["year"] = f"must be between {MIN_YEAR} and {MAX_YEAR}"
    else:
        book["year"] = year

    isbn = payload.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    elif isbn is not None and len(isbn.strip()) > MAX_ISBN_LENGTH:
        errors["isbn"] = f"must be at most {MAX_ISBN_LENGTH} characters"
    else:
        # A blank ISBN carries no information; store it as absent.
        book["isbn"] = (isbn.strip() or None) if isbn is not None else None

    if errors:
        raise ValidationError(errors)
    return book
