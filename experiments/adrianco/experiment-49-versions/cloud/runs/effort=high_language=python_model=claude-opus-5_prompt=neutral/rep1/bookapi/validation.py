"""Input validation for book payloads.

Kept deliberately separate from HTTP and storage concerns so the rules can be
unit tested on their own.
"""

from __future__ import annotations

import re
from typing import Any

MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 255
MIN_YEAR = 1
MAX_YEAR = 9999

# ISBN-10 (9 digits + digit or X) or ISBN-13 (13 digits), once hyphens and
# spaces have been stripped. Checksums are intentionally not verified: the goal
# is to reject obvious junk, not to reject legitimate-but-unusual identifiers.
_ISBN10 = re.compile(r"^\d{9}[\dXx]$")
_ISBN13 = re.compile(r"^\d{13}$")

# Fields a client may send. Anything else in the payload is ignored so that
# round-tripping a response back into a PUT (which includes ``id`` and the
# timestamps) does not fail.
WRITABLE_FIELDS = ("title", "author", "year", "isbn")


class ValidationError(Exception):
    """Raised when a request payload does not satisfy the rules above.

    ``errors`` maps a field name (or ``"body"`` for whole-payload problems) to a
    human readable explanation.
    """

    def __init__(self, errors: dict[str, str], message: str = "Validation failed"):
        super().__init__(message)
        self.message = message
        self.errors = errors


def parse_book(payload: Any) -> dict[str, Any]:
    """Validate and normalise a book payload.

    Returns a dict with exactly the keys ``title``, ``author``, ``year`` and
    ``isbn``. ``title`` and ``author`` are required and whitespace-trimmed;
    ``year`` and ``isbn`` are optional and default to ``None``.

    Raises:
        ValidationError: if the payload is not an object or any field is invalid.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "Request body must be a JSON object."})

    errors: dict[str, str] = {}
    book: dict[str, Any] = {}

    for field, max_length in (
        ("title", MAX_TITLE_LENGTH),
        ("author", MAX_AUTHOR_LENGTH),
    ):
        try:
            book[field] = _required_text(payload, field, max_length)
        except ValidationError as exc:
            errors.update(exc.errors)

    for field, parser in (("year", _optional_year), ("isbn", _optional_isbn)):
        try:
            book[field] = parser(payload.get(field))
        except ValidationError as exc:
            errors.update(exc.errors)

    if errors:
        raise ValidationError(errors)
    return book


def _required_text(payload: dict[str, Any], field: str, max_length: int) -> str:
    if field not in payload or payload[field] is None:
        raise ValidationError({field: f"{field} is required."})

    value = payload[field]
    if not isinstance(value, str):
        raise ValidationError({field: f"{field} must be a string."})

    value = value.strip()
    if not value:
        raise ValidationError({field: f"{field} must not be empty."})
    if len(value) > max_length:
        raise ValidationError(
            {field: f"{field} must be at most {max_length} characters."}
        )
    return value


def _optional_year(value: Any) -> int | None:
    if value is None:
        return None

    # bool is a subclass of int, but True is not a year.
    if isinstance(value, bool):
        raise ValidationError({"year": "year must be an integer."})

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            value = int(stripped)
        except ValueError:
            raise ValidationError({"year": "year must be an integer."}) from None
    elif not isinstance(value, int):
        raise ValidationError({"year": "year must be an integer."})

    if not MIN_YEAR <= value <= MAX_YEAR:
        raise ValidationError(
            {"year": f"year must be between {MIN_YEAR} and {MAX_YEAR}."}
        )
    return value


def _optional_isbn(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError({"isbn": "isbn must be a string."})

    value = value.strip()
    if not value:
        return None

    compact = value.replace("-", "").replace(" ", "")
    if not (_ISBN10.match(compact) or _ISBN13.match(compact)):
        raise ValidationError(
            {"isbn": "isbn must be a valid ISBN-10 or ISBN-13 (hyphens allowed)."}
        )
    return value
