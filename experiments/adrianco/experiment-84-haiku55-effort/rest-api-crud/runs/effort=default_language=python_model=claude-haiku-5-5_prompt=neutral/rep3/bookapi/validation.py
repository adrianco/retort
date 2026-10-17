"""Input validation for book payloads."""

from datetime import date

MAX_TEXT_LENGTH = 500


class ValidationError(Exception):
    """Raised when a payload fails validation. ``errors`` maps field -> message."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload: object) -> dict:
    """Return a cleaned book dict, or raise ``ValidationError``.

    ``title`` and ``author`` are required. ``year`` and ``isbn`` are optional
    and become ``None`` when omitted. Unknown fields are ignored.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    clean = {
        "title": _required_text(payload, "title", errors),
        "author": _required_text(payload, "author", errors),
        "year": _optional_year(payload, "year", errors),
        "isbn": _optional_isbn(payload, "isbn", errors),
    }
    if errors:
        raise ValidationError(errors)
    return clean


def _required_text(payload: dict, field: str, errors: dict[str, str]) -> str | None:
    value = payload.get(field)
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


def _optional_year(payload: dict, field: str, errors: dict[str, str]) -> int | None:
    value = payload.get(field)
    if value is None:
        return None
    # bool is a subclass of int in Python, so exclude it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        errors[field] = "must be an integer"
        return None
    max_year = date.today().year + 1
    if not 1 <= value <= max_year:
        errors[field] = f"must be between 1 and {max_year}"
        return None
    return value


def _optional_isbn(payload: dict, field: str, errors: dict[str, str]) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return None
    normalized = value.replace("-", "").replace(" ", "").upper()
    if not (_valid_isbn10(normalized) or _valid_isbn13(normalized)):
        errors[field] = "must be a valid ISBN-10 or ISBN-13"
        return None
    return normalized


def _valid_isbn10(isbn: str) -> bool:
    if len(isbn) != 10 or not all(c.isdigit() for c in isbn[:9]):
        return False
    if not (isbn[9].isdigit() or isbn[9] == "X"):
        return False
    digits = [10 if c == "X" else int(c) for c in isbn]
    return sum((10 - i) * d for i, d in enumerate(digits)) % 11 == 0


def _valid_isbn13(isbn: str) -> bool:
    if len(isbn) != 13 or not isbn.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn))
    return total % 10 == 0
