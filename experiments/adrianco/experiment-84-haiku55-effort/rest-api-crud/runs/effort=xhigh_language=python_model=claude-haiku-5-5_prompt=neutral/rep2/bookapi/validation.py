"""Input validation for book payloads.

Every problem in a payload is reported at once, so a client can fix them all
in a single round trip.
"""

from __future__ import annotations

import datetime
import re
from typing import Any

MAX_TEXT_LENGTH = 500
# Earliest accepted year. Negative values allow for very old works.
MIN_YEAR = -3000
_ISBN_PATTERN = re.compile(r"[0-9]{9}[0-9X]|[0-9]{13}")


class ValidationError(Exception):
    """A payload failed validation. `errors` maps field name to a message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload: Any) -> dict[str, Any]:
    """Return the cleaned book fields, or raise ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    cleaned = {
        "title": _required_text(payload, "title", errors),
        "author": _required_text(payload, "author", errors),
        "year": _optional_year(payload, "year", errors),
        "isbn": _optional_isbn(payload, "isbn", errors),
    }
    if errors:
        raise ValidationError(errors)
    return cleaned


def _required_text(payload: dict[str, Any], field: str, errors: dict[str, str]) -> str | None:
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    text = value.strip()
    if not text:
        errors[field] = "must not be blank"
        return None
    if len(text) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return text


def _optional_year(payload: dict[str, Any], field: str, errors: dict[str, str]) -> int | None:
    value = payload.get(field)
    if value is None:
        return None
    latest = datetime.date.today().year + 1  # allow books announced for next year
    # bool is a subclass of int, so exclude it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        errors[field] = "must be an integer"
        return None
    if not MIN_YEAR <= value <= latest:
        errors[field] = f"must be between {MIN_YEAR} and {latest}"
        return None
    return value


def _optional_isbn(payload: dict[str, Any], field: str, errors: dict[str, str]) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    # Hyphens and spaces are allowed as separators. The check digit is not verified.
    digits = re.sub(r"[\s-]", "", value).upper()
    if not _ISBN_PATTERN.fullmatch(digits):
        errors[field] = "must be a valid ISBN-10 or ISBN-13"
        return None
    return value.strip()
