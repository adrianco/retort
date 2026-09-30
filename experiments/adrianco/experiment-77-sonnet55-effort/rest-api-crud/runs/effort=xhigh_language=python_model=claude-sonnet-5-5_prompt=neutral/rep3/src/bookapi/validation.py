"""Input validation for book payloads."""

from __future__ import annotations

from typing import Any

MAX_TEXT_LENGTH = 255
MAX_ISBN_LENGTH = 32
MIN_YEAR = 1
MAX_YEAR = 9999


class ValidationError(Exception):
    """Raised when a payload is invalid; ``errors`` maps field name to message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Validation failed")
        self.errors = errors


def _required_text(payload: dict[str, Any], field: str, errors: dict[str, str]) -> str | None:
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    value = value.strip()
    if not value:
        errors[field] = "must not be empty"
        return None
    if len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return value


def _optional_year(payload: dict[str, Any], errors: dict[str, str]) -> int | None:
    value = payload.get("year")
    if value is None:
        return None
    # bool is a subclass of int, but `true` is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
        return None
    if not MIN_YEAR <= value <= MAX_YEAR:
        errors["year"] = f"must be between {MIN_YEAR} and {MAX_YEAR}"
        return None
    return value


def _optional_isbn(payload: dict[str, Any], errors: dict[str, str]) -> str | None:
    value = payload.get("isbn")
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    value = value.strip()
    if len(value) > MAX_ISBN_LENGTH:
        errors["isbn"] = f"must be at most {MAX_ISBN_LENGTH} characters"
        return None
    return value or None


def validate_book(payload: Any) -> dict[str, Any]:
    """Validate a create/replace payload and return the cleaned book fields.

    ``title`` and ``author`` are required; ``year`` and ``isbn`` are optional.
    Unknown keys are ignored. Raises :class:`ValidationError` listing every
    invalid field.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    book = {
        "title": _required_text(payload, "title", errors),
        "author": _required_text(payload, "author", errors),
        "year": _optional_year(payload, errors),
        "isbn": _optional_isbn(payload, errors),
    }
    if errors:
        raise ValidationError(errors)
    return book
