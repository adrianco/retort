"""Validation for book payloads."""

import re

MAX_TEXT_LENGTH = 500
MIN_YEAR = 1
MAX_YEAR = 9999

_ISBN10 = re.compile(r"[0-9]{9}[0-9X]")
_ISBN13 = re.compile(r"[0-9]{13}")


class ValidationError(Exception):
    """A payload failed validation. ``errors`` maps field name to a message."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload):
    """Return a cleaned book dict, or raise ValidationError.

    title and author are required. year and isbn are optional. Unknown fields
    are ignored, so clients cannot set the id.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    book = {
        "title": _required_text(payload, "title", errors),
        "author": _required_text(payload, "author", errors),
        "year": _optional_year(payload.get("year"), errors),
        "isbn": _optional_isbn(payload.get("isbn"), errors),
    }
    if errors:
        raise ValidationError(errors)
    return book


def is_valid_isbn(isbn):
    """Check an ISBN-10 or ISBN-13 (digits only, X allowed as final ISBN-10 digit) and its checksum."""
    if _ISBN13.fullmatch(isbn):
        total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(isbn))
        return total % 10 == 0
    if _ISBN10.fullmatch(isbn):
        values = [10 if char == "X" else int(char) for char in isbn]
        return sum((10 - i) * value for i, value in enumerate(values)) % 11 == 0
    return False


def _required_text(payload, field, errors):
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
    elif not isinstance(value, str):
        errors[field] = "must be a string"
    elif not value.strip():
        errors[field] = "must not be blank"
    elif len(value.strip()) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
    else:
        return value.strip()
    return None


def _optional_year(value, errors):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
    elif not MIN_YEAR <= value <= MAX_YEAR:
        errors["year"] = f"must be between {MIN_YEAR} and {MAX_YEAR}"
    else:
        return value
    return None


def _optional_isbn(value, errors):
    """Hyphens and spaces are stripped and the result is upper-cased. An empty value means no ISBN."""
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    isbn = re.sub(r"[\s-]", "", value).upper()
    if not isbn:
        return None
    if not is_valid_isbn(isbn):
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
        return None
    return isbn
