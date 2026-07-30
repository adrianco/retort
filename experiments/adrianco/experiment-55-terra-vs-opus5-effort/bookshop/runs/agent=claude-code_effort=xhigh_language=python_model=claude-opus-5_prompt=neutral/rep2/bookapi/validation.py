"""Validation and normalisation of incoming book payloads."""

from __future__ import annotations

import re
from datetime import date

MAX_TEXT_LENGTH = 500

# Books predate the printing press, but a year below this is almost certainly a
# typo.  The upper bound leaves room for forthcoming titles.
MIN_YEAR = 1
MAX_YEAR = date.today().year + 1

# ISBN-10 (last character may be the check digit "X") or ISBN-13, once grouping
# hyphens and spaces have been removed.
_ISBN_RE = re.compile(r"^(?:\d{9}[\dX]|\d{13})$")

# Fields a client may supply.  Anything else in the payload is ignored.
FIELDS = ("title", "author", "year", "isbn")


class ValidationError(Exception):
    """Raised when a payload cannot be turned into a valid book.

    ``errors`` maps field name -> human readable problem, so a client learns
    about every mistake in one round trip.
    """

    def __init__(self, errors: dict[str, str], message: str = "Validation failed"):
        super().__init__(message)
        self.message = message
        self.errors = errors


def validate_book(payload: object, *, partial: bool = False) -> dict[str, object]:
    """Return normalised book fields taken from ``payload``.

    With ``partial=False`` (POST/PUT) the result always contains all four
    fields: ``title`` and ``author`` are required and the optional ``year`` and
    ``isbn`` default to ``None`` so the resource is fully replaced.

    With ``partial=True`` (PATCH) only the keys present in the payload are
    returned, letting the caller merge them onto the stored row.
    """
    if not isinstance(payload, dict):
        raise ValidationError({}, "Request body must be a JSON object")

    fields: dict[str, object] = {}
    errors: dict[str, str] = {}

    for name in ("title", "author"):
        if name in payload:
            try:
                fields[name] = _text(payload[name], name)
            except ValueError as exc:
                errors[name] = str(exc)
        elif not partial:
            errors[name] = f"{name} is required"

    for name, parse in (("year", _year), ("isbn", _isbn)):
        if name in payload:
            try:
                fields[name] = parse(payload[name])
            except ValueError as exc:
                errors[name] = str(exc)
        elif not partial:
            fields[name] = None

    if errors:
        raise ValidationError(errors)
    if partial and not fields:
        raise ValidationError(
            {}, "Provide at least one of: " + ", ".join(FIELDS)
        )
    return fields


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{name} must not be blank")
    if len(stripped) > MAX_TEXT_LENGTH:
        raise ValueError(f"{name} must be at most {MAX_TEXT_LENGTH} characters")
    return stripped


def _year(value: object) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int; True is not a publication year.
    if isinstance(value, bool):
        raise ValueError("year must be an integer")
    if isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            raise ValueError("year must be an integer") from None
    if not isinstance(value, int):
        raise ValueError("year must be an integer")
    if not MIN_YEAR <= value <= MAX_YEAR:
        raise ValueError(f"year must be between {MIN_YEAR} and {MAX_YEAR}")
    return value


def _isbn(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("isbn must be a string")
    stripped = value.strip()
    if not stripped:
        return None
    compact = re.sub(r"[\s-]", "", stripped).upper()
    if not _ISBN_RE.match(compact):
        raise ValueError("isbn must be 10 or 13 digits, optionally hyphenated")
    # Store what the client sent (minus surrounding whitespace) so responses
    # echo back the caller's preferred formatting.
    return stripped
