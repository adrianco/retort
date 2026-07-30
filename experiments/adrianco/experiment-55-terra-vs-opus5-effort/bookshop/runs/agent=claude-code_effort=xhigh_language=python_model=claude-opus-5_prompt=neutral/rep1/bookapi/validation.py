"""Input validation for book payloads.

All field problems in one request are collected and reported together, so a
client fixing a bad payload only needs a single round trip.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .errors import ValidationError

MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 200
MAX_ISBN_INPUT_LENGTH = 32
MIN_YEAR = 1
#: Books may be dated one year ahead so upcoming releases can be catalogued.
FUTURE_YEAR_ALLOWANCE = 1

#: 10 digits (last may be an X check character) or 13 digits, after normalising
#: away spaces and hyphens. The check digit itself is not verified.
_ISBN_RE = re.compile(r"^(?:\d{9}[\dX]|\d{13})$")
_ISBN_SEPARATORS = re.compile(r"[\s_-]")

BOOK_FIELDS = ("title", "author", "year", "isbn")
REQUIRED_FIELDS = ("title", "author")


class _FieldError(ValueError):
    """Internal marker for a single-field problem."""


def max_year() -> int:
    return datetime.now(timezone.utc).year + FUTURE_YEAR_ALLOWANCE


def _clean_text(value: Any, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise _FieldError(f"{field} must be a string.")
    text = value.strip()
    if not text:
        raise _FieldError(f"{field} must not be empty.")
    if len(text) > max_length:
        raise _FieldError(f"{field} must be at most {max_length} characters.")
    return text


def _clean_year(value: Any) -> int | None:
    if value is None:
        return None
    # bool is an int subclass; True would otherwise validate as the year 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise _FieldError("year must be an integer or null.")
    upper = max_year()
    if not MIN_YEAR <= value <= upper:
        raise _FieldError(f"year must be between {MIN_YEAR} and {upper}.")
    return value


def _clean_isbn(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _FieldError("isbn must be a string or null.")
    if len(value) > MAX_ISBN_INPUT_LENGTH:
        raise _FieldError("isbn must be a 10- or 13-digit ISBN.")
    normalised = _ISBN_SEPARATORS.sub("", value).upper()
    if not normalised:
        # An explicitly blank ISBN means "no ISBN" rather than an error.
        return None
    if not _ISBN_RE.match(normalised):
        raise _FieldError(
            "isbn must be a 10- or 13-digit ISBN, optionally hyphenated "
            "(e.g. 978-0-452-28423-4)."
        )
    return normalised


_CLEANERS = {
    "title": lambda value: _clean_text(value, "title", MAX_TITLE_LENGTH),
    "author": lambda value: _clean_text(value, "author", MAX_AUTHOR_LENGTH),
    "year": _clean_year,
    "isbn": _clean_isbn,
}


def _validate(payload: Any, *, partial: bool) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    cleaned: dict[str, Any] = {}
    details: dict[str, str] = {}

    for field in BOOK_FIELDS:
        if field in payload:
            try:
                cleaned[field] = _CLEANERS[field](payload[field])
            except _FieldError as exc:
                details[field] = str(exc)
        elif field in REQUIRED_FIELDS and not partial:
            details[field] = f"{field} is required."
        elif not partial:
            # Optional fields default to null on create/replace.
            cleaned[field] = None

    if details:
        raise ValidationError(
            "The submitted book is not valid.",
            details=details,
        )

    if partial and not cleaned:
        raise ValidationError(
            "No updatable fields were provided.",
            details={"fields": f"Provide at least one of: {', '.join(BOOK_FIELDS)}."},
        )

    return cleaned


def validate_book(payload: Any) -> dict[str, Any]:
    """Validate a complete book for POST /books or PUT /books/<id>.

    Returns every field, with omitted optional fields set to ``None``.
    """
    return _validate(payload, partial=False)


def validate_book_patch(payload: Any) -> dict[str, Any]:
    """Validate a partial book for PATCH /books/<id>.

    Returns only the fields the client actually supplied.
    """
    return _validate(payload, partial=True)


def validate_pagination(args: Any) -> tuple[int | None, int]:
    """Parse ``?limit=``/``?offset=`` from a query-string mapping."""
    details: dict[str, str] = {}

    limit: int | None = None
    raw_limit = args.get("limit")
    if raw_limit not in (None, ""):
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            details["limit"] = "limit must be an integer."
        else:
            if not 1 <= limit <= 500:
                details["limit"] = "limit must be between 1 and 500."

    offset = 0
    raw_offset = args.get("offset")
    if raw_offset not in (None, ""):
        try:
            offset = int(raw_offset)
        except (TypeError, ValueError):
            details["offset"] = "offset must be an integer."
        else:
            if offset < 0:
                details["offset"] = "offset must not be negative."

    if details:
        raise ValidationError("Invalid query parameters.", details=details)

    return limit, offset
