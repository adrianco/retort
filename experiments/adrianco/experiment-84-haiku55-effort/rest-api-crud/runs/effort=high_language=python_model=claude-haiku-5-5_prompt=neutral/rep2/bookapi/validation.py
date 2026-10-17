"""Input validation and normalisation for book payloads."""

from __future__ import annotations

import re
from datetime import date

MAX_TEXT_LENGTH = 500
MIN_YEAR = 1000

_ISBN_RE = re.compile(r"[0-9]{9}[0-9X]|[0-9]{13}")


class ValidationError(Exception):
    """A payload failed validation. `errors` maps each bad field to a message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload: object) -> dict[str, object]:
    """Return a normalised book dict, or raise ValidationError listing every problem."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors: dict[str, str] = {}
    title = _required_text(payload, "title", errors)
    author = _required_text(payload, "author", errors)
    year = _optional_year(payload, errors)
    isbn = _optional_isbn(payload, errors)

    if errors:
        raise ValidationError(errors)
    return {"title": title, "author": author, "year": year, "isbn": isbn}


def _required_text(payload: dict, field: str, errors: dict[str, str]) -> str | None:
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


def _optional_year(payload: dict, errors: dict[str, str]) -> int | None:
    value = payload.get("year")
    if value is None:
        return None
    max_year = date.today().year + 1
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
    elif not MIN_YEAR <= value <= max_year:
        errors["year"] = f"must be between {MIN_YEAR} and {max_year}"
    else:
        return value
    return None


def _optional_isbn(payload: dict, errors: dict[str, str]) -> str | None:
    value = payload.get("isbn")
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    # Hyphens and spaces are common in printed ISBNs; store the compact form.
    isbn = value.replace("-", "").replace(" ", "").upper()
    if _ISBN_RE.fullmatch(isbn):
        return isbn
    errors["isbn"] = "must be a valid ISBN-10 or ISBN-13"
    return None
