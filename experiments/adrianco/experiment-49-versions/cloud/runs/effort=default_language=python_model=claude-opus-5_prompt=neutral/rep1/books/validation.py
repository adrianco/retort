"""Payload validation for book resources.

Validation is deliberately dependency-free: it takes the decoded JSON body and
returns a normalized dict, raising :class:`ValidationError` with a per-field
map of problems so the API can answer with a useful 400.
"""

MAX_TEXT_LENGTH = 500
MIN_YEAR = 1
MAX_YEAR = 9999

ALLOWED_FIELDS = {"title", "author", "year", "isbn"}


class ValidationError(Exception):
    """Raised when a request body cannot be turned into a valid book."""

    def __init__(self, errors: dict):
        super().__init__("Validation failed")
        self.errors = errors


def _validate_text(value, field: str, errors: dict):
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    cleaned = value.strip()
    if not cleaned:
        errors[field] = "must not be empty"
        return None
    if len(cleaned) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return cleaned


def _validate_year(value, errors: dict):
    if value is None:
        return None
    # bool is a subclass of int; reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
        return None
    if not MIN_YEAR <= value <= MAX_YEAR:
        errors["year"] = f"must be between {MIN_YEAR} and {MAX_YEAR}"
        return None
    return value


def _isbn10_is_valid(digits: str) -> bool:
    total = 0
    for i, char in enumerate(digits):
        if char == "X" and i != 9:
            return False
        value = 10 if char == "X" else int(char)
        total += value * (10 - i)
    return total % 11 == 0


def _isbn13_is_valid(digits: str) -> bool:
    total = sum(
        int(char) * (1 if i % 2 == 0 else 3) for i, char in enumerate(digits)
    )
    return total % 10 == 0


def _validate_isbn(value, errors: dict):
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    normalized = value.replace("-", "").replace(" ", "").upper()
    if not normalized:
        return None
    if len(normalized) == 10:
        valid = normalized[:9].isdigit() and _isbn10_is_valid(normalized)
    elif len(normalized) == 13:
        valid = normalized.isdigit() and _isbn13_is_valid(normalized)
    else:
        valid = False
    if not valid:
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
        return None
    return normalized


def validate_book(payload) -> dict:
    """Validate a create/replace payload and return normalized book fields.

    ``title`` and ``author`` are required; ``year`` and ``isbn`` are optional
    and default to ``None``.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict = {}

    unknown = sorted(set(payload) - ALLOWED_FIELDS)
    if unknown:
        errors["body"] = f"unknown field(s): {', '.join(unknown)}"

    book = {}
    for field in ("title", "author"):
        if field not in payload:
            errors[field] = "is required"
            continue
        book[field] = _validate_text(payload[field], field, errors)

    book["year"] = _validate_year(payload.get("year"), errors)
    book["isbn"] = _validate_isbn(payload.get("isbn"), errors)

    if errors:
        raise ValidationError(errors)
    return book
