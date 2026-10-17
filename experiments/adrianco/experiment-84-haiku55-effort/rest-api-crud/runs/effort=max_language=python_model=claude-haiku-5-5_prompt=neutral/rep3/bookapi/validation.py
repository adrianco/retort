"""Input validation for book payloads."""

import re
from datetime import date
from typing import Any

from .errors import ApiError

MAX_TEXT_LENGTH = 255
_ISBN10 = re.compile(r"[0-9]{9}[0-9X]")
_ISBN13 = re.compile(r"97[89][0-9]{10}")


def validate_book(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the cleaned fields, or raise a 400 ApiError naming every invalid field."""
    errors: dict[str, str] = {}
    fields = {
        "title": _text(payload.get("title"), "title", errors),
        "author": _text(payload.get("author"), "author", errors),
        "year": _year(payload.get("year"), errors),
        "isbn": _isbn(payload.get("isbn"), errors),
    }
    if errors:
        raise ApiError(400, "Validation failed", errors)
    return fields


def validate_author_filter(author: str | None) -> str | None:
    if author is None:
        return None
    author = author.strip()
    if not author:
        raise ApiError(400, "Validation failed", {"author": "Must not be blank"})
    return author


def normalize_isbn(text: str) -> str | None:
    """Return the ISBN as bare digits (an ISBN-10 may end in X), or None if it is invalid."""
    isbn = re.sub(r"[\s-]", "", text).upper()
    if _is_valid_isbn10(isbn) or _is_valid_isbn13(isbn):
        return isbn
    return None


def _text(value: Any, field: str, errors: dict[str, str]) -> str | None:
    if value is None:
        errors[field] = f"{field.capitalize()} is required"
        return None
    if not isinstance(value, str):
        errors[field] = "Must be a string"
        return None
    value = value.strip()
    if not value:
        errors[field] = "Must not be blank"
        return None
    if len(value) > MAX_TEXT_LENGTH:
        errors[field] = f"Must be at most {MAX_TEXT_LENGTH} characters"
        return None
    return value


def _year(value: Any, errors: dict[str, str]) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "Must be an integer"
        return None
    max_year = date.today().year + 1
    if not 1 <= value <= max_year:
        errors["year"] = f"Must be between 1 and {max_year}"
        return None
    return value


def _isbn(value: Any, errors: dict[str, str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "Must be a string"
        return None
    isbn = normalize_isbn(value)
    if isbn is None:
        errors["isbn"] = "Must be a valid ISBN-10 or ISBN-13"
    return isbn


def _is_valid_isbn10(isbn: str) -> bool:
    if not _ISBN10.fullmatch(isbn):
        return False
    total = sum((10 - i) * (10 if digit == "X" else int(digit)) for i, digit in enumerate(isbn))
    return total % 11 == 0


def _is_valid_isbn13(isbn: str) -> bool:
    if not _ISBN13.fullmatch(isbn):
        return False
    total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(isbn))
    return total % 10 == 0
