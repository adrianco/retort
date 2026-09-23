"""Input validation for book payloads."""

import datetime
import re

FIELDS = ("title", "author", "year", "isbn")
MAX_TEXT_LENGTH = 500
_ISBN_RE = re.compile(r"^(\d{9}[\dX]|\d{13})$")


class ValidationError(Exception):
    """Raised when a payload fails validation; ``errors`` maps field -> message."""

    def __init__(self, errors):
        super().__init__("Validation failed")
        self.errors = errors


def validate_book(payload):
    """Validate a create/replace payload and return a normalised dict.

    ``title`` and ``author`` are required non-empty strings. ``year`` is an
    optional integer no later than next year. ``isbn`` is an optional
    ISBN-10 or ISBN-13; hyphens and spaces are allowed and stripped.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "Request body must be a JSON object"})

    errors = {}
    unknown = sorted(set(payload) - set(FIELDS) - {"id"})
    for field in unknown:
        errors[field] = "Unknown field"

    book = {}
    for field in ("title", "author"):
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors[field] = f"{field.capitalize()} is required"
        elif not isinstance(value, str):
            errors[field] = f"{field.capitalize()} must be a string"
        elif len(value.strip()) > MAX_TEXT_LENGTH:
            errors[field] = f"{field.capitalize()} must be at most {MAX_TEXT_LENGTH} characters"
        else:
            book[field] = value.strip()

    year = payload.get("year")
    max_year = datetime.date.today().year + 1
    if year is None:
        book["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int):
        errors["year"] = "Year must be an integer"
    elif not -5000 <= year <= max_year:
        errors["year"] = f"Year must be between -5000 and {max_year}"
    else:
        book["year"] = year

    isbn = payload.get("isbn")
    if isbn is None or (isinstance(isbn, str) and not isbn.strip()):
        book["isbn"] = None
    elif not isinstance(isbn, str):
        errors["isbn"] = "ISBN must be a string"
    else:
        normalised = re.sub(r"[\s-]", "", isbn).upper()
        if not _ISBN_RE.match(normalised):
            errors["isbn"] = "ISBN must be a valid ISBN-10 or ISBN-13"
        else:
            book["isbn"] = normalised

    if errors:
        raise ValidationError(errors)
    return book
