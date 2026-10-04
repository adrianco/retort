"""Validation of book payloads received from clients."""

from typing import Any

MAX_TEXT_LENGTH = 500
MAX_ISBN_LENGTH = 32
MIN_YEAR = 1
MAX_YEAR = 9999


def validate_book(payload: Any) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate a book payload.

    Returns ``(book, errors)``. ``book`` holds the normalised fields and is
    only meaningful when ``errors`` (field name -> message) is empty. Unknown
    fields are ignored so clients can echo back a full book representation.
    """
    if not isinstance(payload, dict):
        return {}, {"body": "must be a JSON object"}

    book: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for field in ("title", "author"):
        value = payload.get(field)
        if value is None:
            errors[field] = "is required"
            continue
        error = _text_error(value, MAX_TEXT_LENGTH)
        if error is None and not value.strip():
            error = "must not be blank"
        if error is not None:
            errors[field] = error
        else:
            book[field] = value.strip()

    year = payload.get("year")
    # bool is a subclass of int, but true/false is not a year.
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        errors["year"] = "must be an integer"
    elif year is not None and not MIN_YEAR <= year <= MAX_YEAR:
        errors["year"] = f"must be between {MIN_YEAR} and {MAX_YEAR}"
    else:
        book["year"] = year

    isbn = payload.get("isbn")
    error = _text_error(isbn, MAX_ISBN_LENGTH) if isbn is not None else None
    if error is not None:
        errors["isbn"] = error
    else:
        # A blank ISBN carries no information, so store it as "not set".
        book["isbn"] = (isbn.strip() or None) if isbn is not None else None

    return book, errors


def _text_error(value: Any, max_length: int) -> str | None:
    if not isinstance(value, str):
        return "must be a string"
    if len(value.strip()) > max_length:
        return f"must be at most {max_length} characters"
    try:
        # JSON escapes can smuggle in lone surrogates, which SQLite can't store.
        value.encode("utf-8")
    except UnicodeEncodeError:
        return "must be valid Unicode text"
    return None
