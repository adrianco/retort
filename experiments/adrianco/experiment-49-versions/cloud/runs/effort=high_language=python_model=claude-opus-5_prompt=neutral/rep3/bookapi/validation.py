"""Request payload validation for book resources.

Validation collects *every* problem it finds rather than raising on the first
one, so a client gets one round trip per fix-up instead of one per field.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .errors import ApiError

MAX_TEXT_LENGTH = 255
MIN_YEAR = 1
# Publishers routinely date books slightly into the future, so allow a little slack.
MAX_YEAR_SLACK = 1

_ISBN_SEPARATORS = str.maketrans("", "", "- ")


def _validate_text(value: Any, field: str, errors: dict[str, str]) -> str | None:
    if value is None:
        errors[field] = "is required"
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    cleaned = value.strip()
    if not cleaned:
        errors[field] = "must not be empty"
        return None
    if len(cleaned) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return cleaned


def _validate_year(value: Any, errors: dict[str, str]) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int; True is not a publication year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
        return None
    max_year = datetime.now(timezone.utc).year + MAX_YEAR_SLACK
    if not MIN_YEAR <= value <= max_year:
        errors["year"] = f"must be between {MIN_YEAR} and {max_year}"
        return None
    return value


def _isbn10_is_valid(digits: str) -> bool:
    if not (digits[:9].isdigit() and (digits[9].isdigit() or digits[9] == "X")):
        return False
    total = sum((10 - i) * int(d) for i, d in enumerate(digits[:9]))
    total += 10 if digits[9] == "X" else int(digits[9])
    return total % 11 == 0


def _isbn13_is_valid(digits: str) -> bool:
    if not digits.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return total % 10 == 0


def _validate_isbn(value: Any, errors: dict[str, str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    normalised = cleaned.translate(_ISBN_SEPARATORS).upper()
    if len(normalised) not in (10, 13):
        errors["isbn"] = "must be 10 or 13 digits, ignoring hyphens and spaces"
        return None
    if len(normalised) == 10 and not _isbn10_is_valid(normalised):
        errors["isbn"] = "is not a valid ISBN-10: the check digit does not match"
        return None
    if len(normalised) == 13 and not _isbn13_is_valid(normalised):
        errors["isbn"] = "is not a valid ISBN-13: the check digit does not match"
        return None
    return normalised


def validate_book(payload: Any) -> dict[str, Any]:
    """Validate a create/replace payload and return normalised book fields.

    Unknown keys are ignored so that clients can round-trip a full book
    representation (``id``, ``created_at``, ...) straight back to the API.
    """
    if not isinstance(payload, dict):
        raise ApiError(
            400, "invalid_request", "Request body must be a JSON object."
        )

    errors: dict[str, str] = {}
    book = {
        "title": _validate_text(payload.get("title"), "title", errors),
        "author": _validate_text(payload.get("author"), "author", errors),
        "year": _validate_year(payload.get("year"), errors),
        "isbn": _validate_isbn(payload.get("isbn"), errors),
    }
    if errors:
        raise ApiError(
            400,
            "validation_failed",
            "The request body failed validation.",
            details=errors,
        )
    return book
