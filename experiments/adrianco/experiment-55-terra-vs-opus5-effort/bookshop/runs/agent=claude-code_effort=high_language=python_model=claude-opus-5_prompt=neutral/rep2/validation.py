"""Input validation for book payloads.

Keeping validation in its own module means the rules can be unit-tested
without spinning up the Flask app or touching the database.
"""

from __future__ import annotations

import re
from typing import Any

#: Fields a client is allowed to send. Anything else is rejected so that
#: typos (e.g. "athor") fail loudly instead of being silently dropped.
ALLOWED_FIELDS = ("title", "author", "year", "isbn")
REQUIRED_FIELDS = ("title", "author")

MAX_TEXT_LENGTH = 500
MIN_YEAR = 1
MAX_YEAR = 2200

# ISBN-10 (9 digits + digit or X check character) or ISBN-13 (13 digits),
# checked after hyphens/spaces have been stripped. Format only -- the
# check digit is deliberately not verified.
_ISBN_RE = re.compile(r"^(?:\d{9}[\dX]|\d{13})$")


class ValidationError(Exception):
    """Raised when a payload cannot be turned into a valid book.

    ``errors`` maps a field name (or ``"_body"`` for whole-payload problems)
    to a human readable message.
    """

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def parse_book(payload: Any, *, partial: bool = False) -> dict[str, Any]:
    """Validate ``payload`` and return a normalised book dict.

    With ``partial=False`` (POST / PUT) the result always contains all four
    fields, with ``year``/``isbn`` defaulting to ``None``. With
    ``partial=True`` (PATCH) only the supplied fields are returned, and at
    least one known field must be present.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"_body": "request body must be a JSON object"})

    errors: dict[str, str] = {}

    unknown = sorted(set(payload) - set(ALLOWED_FIELDS))
    if unknown:
        errors["_body"] = "unknown field(s): {}; allowed fields are: {}".format(
            ", ".join(unknown), ", ".join(ALLOWED_FIELDS)
        )

    book: dict[str, Any] = {}

    for field in REQUIRED_FIELDS:
        if field not in payload:
            if not partial:
                errors[field] = "is required"
            continue
        try:
            book[field] = _clean_text(field, payload[field])
        except ValidationError as exc:
            errors.update(exc.errors)

    for field, parser in (("year", _clean_year), ("isbn", _clean_isbn)):
        if field not in payload:
            if not partial:
                book[field] = None
            continue
        try:
            book[field] = parser(payload[field])
        except ValidationError as exc:
            errors.update(exc.errors)

    if partial and not book and not errors:
        errors["_body"] = "no updatable fields supplied; expected one of: {}".format(
            ", ".join(ALLOWED_FIELDS)
        )

    if errors:
        raise ValidationError(errors)

    # Stable key order so JSON responses look the same for every book.
    return {field: book[field] for field in ALLOWED_FIELDS if field in book}


def _clean_text(field: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError({field: "must be a string"})
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError({field: "must not be empty"})
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise ValidationError({field: f"must be at most {MAX_TEXT_LENGTH} characters"})
    return cleaned


def _clean_year(value: Any) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, but True is not a publication year.
    if isinstance(value, bool):
        raise ValidationError({"year": "must be an integer"})
    if isinstance(value, int):
        year = value
    elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
        year = int(value.strip())
    else:
        raise ValidationError({"year": "must be an integer"})
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValidationError({"year": f"must be between {MIN_YEAR} and {MAX_YEAR}"})
    return year


def _clean_isbn(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError({"isbn": "must be a string"})
    normalised = re.sub(r"[\s-]", "", value).upper()
    if not normalised:
        return None
    if not _ISBN_RE.match(normalised):
        raise ValidationError(
            {"isbn": "must be a valid ISBN-10 or ISBN-13 (digits, optional hyphens)"}
        )
    return normalised
