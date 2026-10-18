"""Input validation for book payloads."""

from datetime import date

MIN_YEAR = 1


def _max_year():
    return date.today().year + 1


def _isbn10_valid(digits):
    if len(digits) != 10 or not digits[:9].isdigit() or not (digits[9].isdigit() or digits[9] == "X"):
        return False
    total = sum((i + 1) * int(c) for i, c in enumerate(digits[:9]))
    total += 10 * 10 if digits[9] == "X" else 10 * int(digits[9])
    return total % 11 == 0


def _isbn13_valid(digits):
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(digits))
    return total % 10 == 0


def normalize_isbn(value):
    """Strip hyphens/spaces and upper-case the check character."""
    return value.replace("-", "").replace(" ", "").upper()


def is_valid_isbn(value):
    cleaned = normalize_isbn(value)
    if len(cleaned) == 10:
        return _isbn10_valid(cleaned)
    if len(cleaned) == 13:
        return _isbn13_valid(cleaned)
    return False


def validate_book(data):
    """Validate a book payload.

    Returns ``(clean, None)`` on success or ``(None, errors)`` where ``errors``
    maps field names to human-readable messages.
    """
    if not isinstance(data, dict):
        return None, {"body": "must be a JSON object"}

    errors = {}
    clean = {}

    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            clean[field] = value.strip()

    year = data.get("year")
    if year is None:
        clean["year"] = None
    elif isinstance(year, bool) or not isinstance(year, int) or not (MIN_YEAR <= year <= _max_year()):
        errors["year"] = f"must be an integer between {MIN_YEAR} and {_max_year()}"
    else:
        clean["year"] = year

    isbn = data.get("isbn")
    if isbn is None:
        clean["isbn"] = None
    elif not isinstance(isbn, str) or not is_valid_isbn(isbn):
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
    else:
        clean["isbn"] = normalize_isbn(isbn)

    if errors:
        return None, errors
    return clean, None
