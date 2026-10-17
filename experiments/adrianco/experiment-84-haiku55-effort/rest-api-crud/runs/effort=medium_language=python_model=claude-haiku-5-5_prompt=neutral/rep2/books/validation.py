"""Input validation for book payloads."""

import datetime
import re

MAX_TEXT_LENGTH = 255


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def parse_book(payload):
    """Validate a book payload and return its normalised fields.

    Raises ValidationError with a field -> message mapping when invalid.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    title = _required_text(payload, "title", errors)
    author = _required_text(payload, "author", errors)
    year = _optional_year(payload, "year", errors)
    isbn = _optional_isbn(payload, "isbn", errors)

    if errors:
        raise ValidationError(errors)
    return {"title": title, "author": author, "year": year, "isbn": isbn}


def _required_text(payload, field, errors):
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
        return None
    if not isinstance(value, str) or not value.strip():
        errors[field] = "must be a non-empty string"
        return None
    value = value.strip()
    if len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return value


def _optional_year(payload, field, errors):
    value = payload.get(field)
    if value is None:
        return None
    max_year = datetime.date.today().year + 1
    # bool is a subclass of int in Python, so reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= max_year:
        errors[field] = f"must be an integer between 1 and {max_year}"
        return None
    return value


def _optional_isbn(payload, field, errors):
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    # Hyphens and spaces are common formatting; store the canonical form so
    # the same ISBN can't be entered twice in different shapes.
    isbn = re.sub(r"[\s-]", "", value).upper()
    if not _is_valid_isbn(isbn):
        errors[field] = "must be a valid ISBN-10 or ISBN-13"
        return None
    return isbn


def _is_valid_isbn(isbn):
    if len(isbn) == 10 and re.fullmatch(r"[0-9]{9}[0-9X]", isbn):
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(isbn))
        return total % 11 == 0
    if len(isbn) == 13 and re.fullmatch(r"[0-9]{13}", isbn):
        total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(isbn))
        return total % 10 == 0
    return False
