"""Input validation for book payloads."""

import datetime
import re

TITLE_MAX_LENGTH = 500
AUTHOR_MAX_LENGTH = 300

_ISBN_SEPARATORS = re.compile(r"[\s-]")
_ISBN10_FORMAT = re.compile(r"[0-9]{9}[0-9X]")
_ISBN13_FORMAT = re.compile(r"[0-9]{13}")


class ValidationError(Exception):
    """A payload failed validation. ``errors`` maps field name to a message."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload):
    """Return a cleaned book dict, or raise ValidationError.

    Used for both create and update: PUT replaces the whole record, so the
    same rules apply. ``title`` and ``author`` are required. ``year`` and
    ``isbn`` are optional; a missing or blank ISBN is stored as null.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    cleaned = {
        "title": _required_text(payload, "title", TITLE_MAX_LENGTH, errors),
        "author": _required_text(payload, "author", AUTHOR_MAX_LENGTH, errors),
        "year": _optional_year(payload, errors),
        "isbn": _optional_isbn(payload, errors),
    }
    if errors:
        raise ValidationError(errors)
    return cleaned


def _required_text(payload, field, max_length, errors):
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
    elif not isinstance(value, str):
        errors[field] = "must be a string"
    elif not value.strip():
        errors[field] = "is required"
    elif len(value.strip()) > max_length:
        errors[field] = f"must be at most {max_length} characters"
    else:
        return value.strip()
    return None


def _optional_year(payload, errors):
    value = payload.get("year")
    if value is None:
        return None
    max_year = datetime.date.today().year + 1
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
    elif not 1 <= value <= max_year:
        errors["year"] = f"must be between 1 and {max_year}"
    else:
        return value
    return None


def _optional_isbn(payload, errors):
    value = payload.get("isbn")
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    isbn = _ISBN_SEPARATORS.sub("", value).upper()
    if not isbn:
        return None
    if not _is_valid_isbn(isbn):
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
        return None
    return isbn


def _is_valid_isbn(isbn):
    """Check format and checksum of a normalised (hyphen-free, upper-case) ISBN."""
    if len(isbn) == 10 and _ISBN10_FORMAT.fullmatch(isbn):
        return _isbn10_checksum_ok(isbn)
    if len(isbn) == 13 and _ISBN13_FORMAT.fullmatch(isbn):
        return _isbn13_checksum_ok(isbn)
    return False


def _isbn10_checksum_ok(isbn):
    total = sum((10 - i) * int(digit) for i, digit in enumerate(isbn[:9]))
    total += 10 if isbn[9] == "X" else int(isbn[9])
    return total % 11 == 0


def _isbn13_checksum_ok(isbn):
    total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(isbn[:12]))
    return (10 - total % 10) % 10 == int(isbn[12])
