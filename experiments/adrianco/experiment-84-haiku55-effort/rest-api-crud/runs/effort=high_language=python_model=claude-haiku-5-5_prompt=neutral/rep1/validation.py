"""Input validation for book payloads."""

import re
from datetime import date

MIN_YEAR = 1000
MAX_TEXT_LENGTH = 500
ISBN_PATTERN = re.compile(r"[0-9]{9}[0-9X]|[0-9]{13}")


class ValidationError(ValueError):
    """Raised when a payload fails validation.

    `fields` maps each offending field name to a human-readable message.
    """

    def __init__(self, fields):
        super().__init__("validation failed")
        self.fields = fields


def validate_book(data):
    """Validate a book payload and return the cleaned fields.

    title and author are required. year and isbn are optional and become None
    when absent. Unknown fields are ignored. Errors for every field are
    collected and raised together.
    """
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    book = {
        "title": _text(data, "title", errors),
        "author": _text(data, "author", errors),
        "year": _year(data.get("year"), errors),
        "isbn": _isbn(data.get("isbn"), errors),
    }
    if errors:
        raise ValidationError(errors)
    return book


def _text(data, field, errors):
    value = data.get(field)
    if value is None:
        errors[field] = "is required"
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    value = value.strip()
    if not value:
        errors[field] = "must not be blank"
        return None
    if len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return value


def _year(value, errors):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
        return None
    max_year = date.today().year + 1
    if not MIN_YEAR <= value <= max_year:
        errors["year"] = f"must be between {MIN_YEAR} and {max_year}"
        return None
    return value


def _isbn(value, errors):
    """Accept ISBN-10 or ISBN-13, with or without hyphens/spaces.

    The format is checked but the check digit is not. The stored value has
    hyphens and spaces removed and is upper-cased.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    cleaned = value.replace("-", "").replace(" ", "").upper()
    if not ISBN_PATTERN.fullmatch(cleaned):
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
        return None
    return cleaned
