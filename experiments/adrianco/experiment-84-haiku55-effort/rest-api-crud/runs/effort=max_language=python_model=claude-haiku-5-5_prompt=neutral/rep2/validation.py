"""Input validation for book payloads and query parameters.

Errors are collected per field so a client can fix every problem in one round trip.
"""

import re
from datetime import date

MIN_YEAR = 1
# ISBN-10 (last character may be X) or ISBN-13, once hyphens and spaces are removed.
ISBN_PATTERN = re.compile(r"[0-9]{9}[0-9Xx]|[0-9]{13}")


class ValidationError(Exception):
    """A request was rejected. ``errors`` maps each invalid field to a message."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("Validation failed.")
        self.errors = errors


def parse_book(payload: dict) -> dict:
    """Validate a book payload and return its cleaned fields.

    ``title`` and ``author`` are required. ``year`` and ``isbn`` are optional;
    omitting them or sending null stores NULL.
    """
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


def parse_author_filter(value: str | None) -> str | None:
    """Validate the optional ``author`` query parameter."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValidationError({"author": "must not be blank"})
    return value


def _required_text(payload: dict, field: str, errors: dict[str, str]) -> str | None:
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
    elif not isinstance(value, str):
        errors[field] = "must be a string"
    elif not value.strip():
        errors[field] = "must not be blank"
    else:
        return value.strip()
    return None


def _optional_year(payload: dict, errors: dict[str, str]) -> int | None:
    year = payload.get("year")
    if year is None:
        return None
    if isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "must be an integer"
    elif not MIN_YEAR <= year <= _max_year():
        errors["year"] = f"must be between {MIN_YEAR} and {_max_year()}"
    else:
        return year
    return None


def _optional_isbn(payload: dict, errors: dict[str, str]) -> str | None:
    isbn = payload.get("isbn")
    if isbn is None:
        return None
    if not isinstance(isbn, str):
        errors["isbn"] = "must be a string"
    elif not ISBN_PATTERN.fullmatch(re.sub(r"[\s-]", "", isbn)):
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
    else:
        return isbn.strip()
    return None


def _max_year() -> int:
    # Allow next year for forthcoming books; a year further ahead is probably a typo.
    return date.today().year + 1
