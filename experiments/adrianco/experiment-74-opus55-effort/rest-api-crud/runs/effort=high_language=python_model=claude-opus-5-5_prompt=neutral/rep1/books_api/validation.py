"""Validation of book payloads."""

import datetime
import re

ALLOWED_FIELDS = {"title", "author", "year", "isbn"}
MAX_TEXT_LENGTH = 500
MIN_YEAR = -5000
_ISBN_RE = re.compile(r"^(\d{9}[\dX]|\d{13})$")


def validate_book(payload):
    """Validate a book payload.

    Returns ``(book, errors)`` where ``book`` is a normalised dict (strings
    stripped, ISBN without hyphens/spaces) and ``errors`` maps field names to
    messages. ``book`` is ``None`` if there are any errors.
    """
    if not isinstance(payload, dict):
        return None, {"body": "request body must be a JSON object"}

    errors = {}
    book = {}

    for field in sorted(set(payload) - ALLOWED_FIELDS):
        errors[field] = "unknown field"

    for field in ("title", "author"):
        value = payload.get(field)
        if value is None:
            errors[field] = f"{field} is required"
        elif not isinstance(value, str):
            errors[field] = f"{field} must be a string"
        elif not value.strip():
            errors[field] = f"{field} must not be empty"
        elif len(value.strip()) > MAX_TEXT_LENGTH:
            errors[field] = f"{field} must be at most {MAX_TEXT_LENGTH} characters"
        else:
            book[field] = value.strip()

    year = payload.get("year")
    if year is not None:
        max_year = datetime.date.today().year + 1
        # bool is a subclass of int; reject it explicitly.
        if isinstance(year, bool) or not isinstance(year, int):
            errors["year"] = "year must be an integer"
        elif not MIN_YEAR <= year <= max_year:
            errors["year"] = f"year must be between {MIN_YEAR} and {max_year}"
        else:
            book["year"] = year
    else:
        book["year"] = None

    isbn = payload.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            errors["isbn"] = "isbn must be a string"
        else:
            normalised = re.sub(r"[\s-]", "", isbn).upper()
            if not normalised:
                book["isbn"] = None
            elif not _ISBN_RE.match(normalised):
                errors["isbn"] = "isbn must be a 10- or 13-digit ISBN"
            else:
                book["isbn"] = normalised
    else:
        book["isbn"] = None

    if errors:
        return None, errors
    return book, {}
