"""Input validation for book payloads.

Rules:
  title   required, non-empty string (<= 500 chars)
  author  required, non-empty string (<= 500 chars)
  year    optional integer between 1000 and next calendar year
  isbn    optional string; hyphens/spaces are stripped and the result must be a
          10-digit (last digit may be 'X') or 13-digit ISBN
"""

import datetime

MAX_TEXT_LEN = 500
MIN_YEAR = 1000

ALLOWED_FIELDS = {"title", "author", "year", "isbn"}


class ValidationError(Exception):
    """Raised when a payload fails validation. ``errors`` maps field -> message."""

    def __init__(self, errors):
        super().__init__("Validation failed")
        self.errors = errors


def _max_year():
    return datetime.date.today().year + 1


def _validate_text(value, field, errors):
    if value is None:
        errors[field] = f"'{field}' is required"
        return None
    if not isinstance(value, str):
        errors[field] = f"'{field}' must be a string"
        return None
    cleaned = value.strip()
    if not cleaned:
        errors[field] = f"'{field}' must not be empty"
        return None
    if len(cleaned) > MAX_TEXT_LEN:
        errors[field] = f"'{field}' must be at most {MAX_TEXT_LEN} characters"
        return None
    return cleaned


def _validate_year(value, errors):
    if value is None:
        return None
    # bool is a subclass of int, but True is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "'year' must be an integer"
        return None
    if not MIN_YEAR <= value <= _max_year():
        errors["year"] = f"'year' must be between {MIN_YEAR} and {_max_year()}"
        return None
    return value


def normalize_isbn(value):
    """Strip hyphens/spaces and upper-case the ISBN check digit."""
    return value.replace("-", "").replace(" ", "").upper()


def _validate_isbn(value, errors):
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "'isbn' must be a string"
        return None
    cleaned = normalize_isbn(value)
    if not cleaned:
        return None
    if len(cleaned) == 10 and cleaned[:9].isdigit() and cleaned[9] in "0123456789X":
        return cleaned
    if len(cleaned) == 13 and cleaned.isdigit():
        return cleaned
    errors["isbn"] = "'isbn' must be a 10- or 13-character ISBN"
    return None


def validate_book(payload):
    """Validate a full book payload (used by both POST and PUT).

    Returns a dict with keys title, author, year, isbn.
    Raises ValidationError with per-field messages otherwise.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "request body must be a JSON object"})

    errors = {}

    unknown = sorted(set(payload) - ALLOWED_FIELDS)
    if unknown:
        errors["body"] = f"unknown field(s): {', '.join(unknown)}"

    book = {
        "title": _validate_text(payload.get("title"), "title", errors),
        "author": _validate_text(payload.get("author"), "author", errors),
        "year": _validate_year(payload.get("year"), errors),
        "isbn": _validate_isbn(payload.get("isbn"), errors),
    }

    if errors:
        raise ValidationError(errors)
    return book
