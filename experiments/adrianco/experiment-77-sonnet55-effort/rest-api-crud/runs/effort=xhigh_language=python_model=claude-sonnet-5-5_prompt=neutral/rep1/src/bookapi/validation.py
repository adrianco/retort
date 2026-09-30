"""Input validation for book payloads."""

from typing import Any

MAX_TEXT_LENGTH = 255
MAX_ISBN_LENGTH = 32
MIN_YEAR = 0
MAX_YEAR = 9999

REQUIRED_FIELDS = ("title", "author")
OPTIONAL_FIELDS = ("year", "isbn")


def _clean_text(name: str, value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, f"{name} must be a string"
    value = value.strip()
    if not value:
        return None, f"{name} must not be empty"
    if len(value) > MAX_TEXT_LENGTH:
        return None, f"{name} must be at most {MAX_TEXT_LENGTH} characters"
    return value, None


def _clean_year(value: Any) -> tuple[int | None, str | None]:
    if value is None:
        return None, None
    # bool is a subclass of int; True is not a plausible year.
    if isinstance(value, bool) or not isinstance(value, int):
        return None, "year must be an integer"
    if not MIN_YEAR <= value <= MAX_YEAR:
        return None, f"year must be between {MIN_YEAR} and {MAX_YEAR}"
    return value, None


def _clean_isbn(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "isbn must be a string"
    value = value.strip()
    if len(value) > MAX_ISBN_LENGTH:
        return None, f"isbn must be at most {MAX_ISBN_LENGTH} characters"
    return (value or None), None


_CLEANERS = {
    "title": lambda v: _clean_text("title", v),
    "author": lambda v: _clean_text("author", v),
    "year": _clean_year,
    "isbn": _clean_isbn,
}


def validate_book(
    payload: dict[str, Any], *, partial: bool = False
) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate a book payload.

    Returns ``(fields, errors)``. ``fields`` holds the cleaned values for every
    recognised key present in the payload (unknown keys are ignored); ``errors``
    maps field name to a message and is empty when the payload is valid.

    With ``partial=False`` (create) ``title`` and ``author`` must be present.
    With ``partial=True`` (update) any subset of fields may be sent, but every
    field that is sent must still be valid.
    """
    fields: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for name in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        if name not in payload:
            if name in REQUIRED_FIELDS and not partial:
                errors[name] = f"{name} is required"
            continue
        cleaned, error = _CLEANERS[name](payload[name])
        if error:
            errors[name] = error
        else:
            fields[name] = cleaned

    return fields, errors
