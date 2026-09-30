"""Input validation for book payloads."""

from __future__ import annotations

from typing import Any

MAX_TEXT_LENGTH = 500
MAX_ISBN_LENGTH = 32
MIN_YEAR = 0
MAX_YEAR = 9999

BOOK_FIELDS = ("title", "author", "year", "isbn")
REQUIRED_FIELDS = ("title", "author")


def _clean_required_text(field: str, value: Any, errors: dict[str, str]) -> str | None:
    if not isinstance(value, str):
        errors[field] = f"{field} must be a string"
        return None
    value = value.strip()
    if not value:
        errors[field] = f"{field} is required and must not be blank"
        return None
    if len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"{field} must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return value


def _clean_year(value: Any, errors: dict[str, str]) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int; `true` is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "year must be an integer"
        return None
    if not MIN_YEAR <= value <= MAX_YEAR:
        errors["year"] = f"year must be between {MIN_YEAR} and {MAX_YEAR}"
        return None
    return value


def _clean_isbn(value: Any, errors: dict[str, str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "isbn must be a string"
        return None
    value = value.strip()
    if len(value) > MAX_ISBN_LENGTH:
        errors["isbn"] = f"isbn must be at most {MAX_ISBN_LENGTH} characters"
        return None
    return value or None


def validate_book(payload: Any, *, partial: bool = False) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate a book payload.

    Returns ``(clean, errors)``. ``errors`` maps field name to message and is
    empty when the payload is valid.

    With ``partial=False`` (create) title and author are required and the
    optional fields default to ``None``. With ``partial=True`` (update) only
    the fields present in the payload are validated and returned; at least one
    known field must be supplied. Unknown keys (including ``id``) are ignored.
    """
    if not isinstance(payload, dict):
        return {}, {"body": "request body must be a JSON object"}

    errors: dict[str, str] = {}
    clean: dict[str, Any] = {}

    if partial and not any(f in payload for f in BOOK_FIELDS):
        return {}, {"body": f"provide at least one of: {', '.join(BOOK_FIELDS)}"}

    for field in REQUIRED_FIELDS:
        if field in payload:
            value = _clean_required_text(field, payload[field], errors)
            if value is not None:
                clean[field] = value
        elif not partial:
            errors[field] = f"{field} is required"

    if "year" in payload:
        year = _clean_year(payload["year"], errors)
        if "year" not in errors:
            clean["year"] = year
    elif not partial:
        clean["year"] = None

    if "isbn" in payload:
        isbn = _clean_isbn(payload["isbn"], errors)
        if "isbn" not in errors:
            clean["isbn"] = isbn
    elif not partial:
        clean["isbn"] = None

    return clean, errors
