"""Validation for book payloads.

Types are checked strictly: a JSON string is never accepted where an integer
is expected, and booleans are not integers. ISBNs are checked for format only;
the check digit is not verified.
"""

import datetime
import re
from typing import Any

MAX_TEXT_LENGTH = 255
MIN_YEAR = 1
ALL_FIELDS = ("title", "author", "year", "isbn")

# ISBN-10 (the last character may be X) or ISBN-13, once hyphens and spaces are removed.
_ISBN_PATTERN = re.compile(r"[0-9]{9}[0-9Xx]|[0-9]{13}")


class ValidationError(Exception):
    """A payload failed validation. ``errors`` maps field name to a message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("Validation failed")
        self.errors = errors


def validate_book(payload: Any, *, partial: bool = False) -> dict[str, Any]:
    """Return the validated fields of ``payload``.

    ``partial=False`` is for creating a book. ``title`` and ``author`` are
    required, and the result always holds all four fields; absent optional
    fields become None.

    ``partial=True`` is for updates. Only the fields present are validated and
    returned, and at least one must be present. An explicit ``null`` clears
    ``year`` or ``isbn``.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})
    if partial and not any(field in payload for field in ALL_FIELDS):
        raise ValidationError({"body": f"must include at least one of: {', '.join(ALL_FIELDS)}"})

    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}

    for field in ("title", "author"):
        if field not in payload:
            if not partial:
                errors[field] = "is required"
            continue
        error = _text_error(payload[field])
        if error:
            errors[field] = error
        else:
            cleaned[field] = payload[field].strip()

    if "year" in payload:
        year = payload["year"]
        error = None if year is None else _year_error(year)
        if error:
            errors["year"] = error
        else:
            cleaned["year"] = year
    elif not partial:
        cleaned["year"] = None

    if "isbn" in payload:
        isbn = payload["isbn"]
        if isbn is None or (isinstance(isbn, str) and not isbn.strip()):
            cleaned["isbn"] = None  # a blank ISBN means "not provided"
        else:
            error = _isbn_error(isbn)
            if error:
                errors["isbn"] = error
            else:
                cleaned["isbn"] = isbn.strip()
    elif not partial:
        cleaned["isbn"] = None

    if errors:
        raise ValidationError(errors)
    return cleaned


def _text_error(value: Any) -> str | None:
    if not isinstance(value, str):
        return "must be a string"
    stripped = value.strip()
    if not stripped:
        return "must not be empty"
    if len(stripped) > MAX_TEXT_LENGTH:
        return f"must be at most {MAX_TEXT_LENGTH} characters"
    return None


def _year_error(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return "must be an integer"
    latest = datetime.date.today().year + 1  # allow books announced for next year
    if not MIN_YEAR <= value <= latest:
        return f"must be between {MIN_YEAR} and {latest}"
    return None


def _isbn_error(value: Any) -> str | None:
    if not isinstance(value, str):
        return "must be a string"
    if not _ISBN_PATTERN.fullmatch(re.sub(r"[\s-]", "", value)):
        return "must be a valid ISBN-10 or ISBN-13"
    return None
