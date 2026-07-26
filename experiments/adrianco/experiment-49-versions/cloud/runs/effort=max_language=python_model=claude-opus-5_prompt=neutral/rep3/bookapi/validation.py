"""Request-body validation for the book resource.

``parse_book`` is the single entry point. It returns a dict containing only
known, cleaned fields, so callers can hand the result straight to the
repository layer without re-checking anything.
"""

from __future__ import annotations

from typing import Any

from .errors import ValidationError

#: Fields a client may supply, in the order they appear in responses.
FIELDS: tuple[str, ...] = ("title", "author", "year", "isbn")

#: Fields that must be present and non-null on a create or a full replace.
REQUIRED_FIELDS: tuple[str, ...] = ("title", "author")

MAX_TEXT_LENGTH = 512
MAX_ISBN_LENGTH = 32
MIN_YEAR = -3000
MAX_YEAR = 3000


class _FieldError(Exception):
    """Internal signal that one field is invalid; collected into `details`."""


def parse_book(payload: Any, *, partial: bool = False) -> dict[str, Any]:
    """Validate a request body and return the cleaned fields it contains.

    Args:
        payload: The decoded JSON body. Must be an object.
        partial: When ``True`` (PATCH), only the supplied fields are validated
            and at least one must be present. When ``False`` (POST/PUT), the
            required fields must be present too.

    Returns:
        A dict whose keys are a subset of :data:`FIELDS`, with values cleaned
        (text stripped, year coerced to ``int``, blank ISBN normalised to
        ``None``).

    Raises:
        ValidationError: With per-field messages under ``details``.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    parsers = {
        "title": lambda value: _text(value, "title"),
        "author": lambda value: _text(value, "author"),
        "year": _year,
        "isbn": _isbn,
    }

    data: dict[str, Any] = {}
    details: dict[str, str] = {}

    for field in FIELDS:
        if field not in payload:
            # Unknown keys in the payload (including "id") are ignored rather
            # than rejected, so a client can round-trip a GET response to PUT.
            if field in REQUIRED_FIELDS and not partial:
                details[field] = f"'{field}' is required."
            continue

        value = payload[field]
        if value is None and field in REQUIRED_FIELDS:
            details[field] = f"'{field}' must not be null."
            continue

        try:
            data[field] = parsers[field](value)
        except _FieldError as error:
            details[field] = str(error)

    if details:
        raise ValidationError(details=details)

    if partial and not data:
        raise ValidationError(
            "Provide at least one field to update: " + ", ".join(FIELDS) + "."
        )

    return data


def _text(value: Any, field: str) -> str:
    """Validate a required, human-readable string field."""
    if not isinstance(value, str):
        raise _FieldError(f"'{field}' must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise _FieldError(f"'{field}' must not be empty.")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise _FieldError(
            f"'{field}' must be at most {MAX_TEXT_LENGTH} characters."
        )
    return cleaned


def _year(value: Any) -> int | None:
    """Validate the optional publication year.

    Accepts an integer, a whole-valued float, or a numeric string; anything
    else (including booleans, which are ints in Python) is rejected.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        raise _FieldError("'year' must be an integer.")
    if isinstance(value, int):
        year = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise _FieldError("'year' must be a whole number.")
        year = int(value)
    elif isinstance(value, str):
        try:
            year = int(value.strip())
        except ValueError:
            raise _FieldError("'year' must be an integer.") from None
    else:
        raise _FieldError("'year' must be an integer.")

    if not MIN_YEAR <= year <= MAX_YEAR:
        raise _FieldError(f"'year' must be between {MIN_YEAR} and {MAX_YEAR}.")
    return year


def _isbn(value: Any) -> str | None:
    """Validate the optional ISBN.

    Only shape is checked, not the ISBN-10/13 check digit: the service stores
    identifiers supplied by its clients and should not reject legitimate but
    unusual ones. A blank string is treated as "not supplied".
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise _FieldError("'isbn' must be a string.")
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_ISBN_LENGTH:
        raise _FieldError(f"'isbn' must be at most {MAX_ISBN_LENGTH} characters.")
    return cleaned
