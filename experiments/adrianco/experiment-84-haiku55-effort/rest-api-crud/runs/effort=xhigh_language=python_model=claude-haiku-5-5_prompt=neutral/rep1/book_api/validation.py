"""Validation and normalisation of book payloads received from clients."""

import re
from collections.abc import Mapping
from typing import Any

from .models import BookFields

MIN_YEAR = 1450  # Roughly the start of movable-type printing in Europe.
MAX_YEAR = 2100
MAX_TEXT_LENGTH = 500

_ISBN_CHARS = re.compile(r"[\s-]")
_ISBN_FORMAT = re.compile(r"[0-9]{9}[0-9X]|[0-9]{13}")


class ValidationError(Exception):
    """Raised when one or more fields of a book payload are invalid."""

    def __init__(self, details: dict[str, str]):
        super().__init__("; ".join(f"{field} {msg}" for field, msg in details.items()))
        self.details = details


def validate_book(payload: Mapping[str, Any]) -> BookFields:
    """Validate a create/replace payload and return normalised fields.

    ``title`` and ``author`` are required. ``year`` and ``isbn`` are optional;
    an absent or null value is stored as ``None``. Unknown keys are ignored.
    All field errors are collected and reported together.
    """
    errors: dict[str, str] = {}
    title = _required_text(payload, "title", errors)
    author = _required_text(payload, "author", errors)
    year = _optional_year(payload, errors)
    isbn = _optional_isbn(payload, errors)

    if errors:
        raise ValidationError(errors)
    return BookFields(title=title, author=author, year=year, isbn=isbn)


def _required_text(payload: Mapping[str, Any], field: str, errors: dict[str, str]) -> str:
    value = payload.get(field)
    if value is None:
        errors[field] = "is required"
        return ""
    if not isinstance(value, str):
        errors[field] = "must be a string"
        return ""
    value = value.strip()
    if not value:
        errors[field] = "must not be blank"
    elif len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"must be at most {MAX_TEXT_LENGTH} characters"
    return value


def _optional_year(payload: Mapping[str, Any], errors: dict[str, str]) -> int | None:
    value = payload.get("year")
    if value is None:
        return None
    # bool is a subclass of int in Python, but true/false is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "must be an integer"
        return None
    if not MIN_YEAR <= value <= MAX_YEAR:
        errors["year"] = f"must be between {MIN_YEAR} and {MAX_YEAR}"
        return None
    return value


def _optional_isbn(payload: Mapping[str, Any], errors: dict[str, str]) -> str | None:
    value = payload.get("isbn")
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "must be a string"
        return None
    # Hyphens and spaces are formatting only; store the canonical digits form.
    cleaned = _ISBN_CHARS.sub("", value).upper()
    if not cleaned:
        return None
    if not _ISBN_FORMAT.fullmatch(cleaned):
        errors["isbn"] = "must be a valid ISBN-10 or ISBN-13 (checksum not verified)"
        return None
    return cleaned
