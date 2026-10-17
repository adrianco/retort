"""Input validation for book payloads."""

import datetime

MAX_YEAR = datetime.date.today().year + 1


class ValidationError(Exception):
    """Raised when a payload fails validation. ``errors`` maps field name to message."""

    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload):
    """Validate a create/update payload and return a normalised dict of book fields.

    ``title`` and ``author`` are required non-blank strings. ``year`` (positive
    integer) and ``isbn`` (string) are optional and may be null.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    title = _required_string(payload, "title", errors)
    author = _required_string(payload, "author", errors)
    year = _optional_year(payload, errors)
    isbn = _optional_string(payload, "isbn", errors)

    if errors:
        raise ValidationError(errors)
    return {"title": title, "author": author, "year": year, "isbn": isbn}


def _required_string(payload, field, errors):
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
        return None
    if not isinstance(value, str) or not value.strip():
        errors[field] = "must be a non-empty string"
        return None
    return value.strip()


def _optional_string(payload, field, errors):
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors[field] = "must be a non-empty string when provided"
        return None
    return value.strip()


def _optional_year(payload, errors):
    value = payload.get("year")
    if value is None:
        return None
    # bool is a subclass of int in Python; reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int) or not (0 < value <= MAX_YEAR):
        errors["year"] = f"must be an integer between 1 and {MAX_YEAR}"
        return None
    return value
