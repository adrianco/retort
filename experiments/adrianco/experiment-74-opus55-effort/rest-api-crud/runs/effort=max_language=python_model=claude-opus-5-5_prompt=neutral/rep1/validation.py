"""Validation of the book payloads that API clients send."""

import re
from datetime import date
from typing import Any

#: Longest title or author accepted, in characters.
MAX_TEXT_LENGTH = 500

#: Fields a client may send but which are ignored. The server assigns ``id``;
#: tolerating it lets a client PUT back a book exactly as it was fetched.
IGNORED_FIELDS = frozenset({"id"})

_ISBN_SEPARATORS = re.compile(r"[\s-]")
_ISBN10 = re.compile(r"[0-9]{9}[0-9X]")
_ISBN13 = re.compile(r"[0-9]{13}")


class ValidationError(ValueError):
    """A rejected payload; ``details`` maps each offending field to the reason."""

    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def validate_book(payload: Any) -> dict[str, Any]:
    """Return the cleaned ``title``, ``author``, ``year`` and ``isbn`` of *payload*.

    Raises ValidationError naming every invalid field, not just the first.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")
    errors = {
        name: "unknown field"
        for name in payload
        if name not in _CLEANERS and name not in IGNORED_FIELDS
    }
    book = {}
    for name, clean in _CLEANERS.items():
        try:
            book[name] = clean(name, payload.get(name))
        except ValueError as exc:
            errors[name] = str(exc)
    if errors:
        raise ValidationError("Invalid book data", errors)
    return book


def _required_text(name: str, value: Any) -> str:
    if isinstance(value, str):
        value = value.strip()
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if len(value) > MAX_TEXT_LENGTH:
        raise ValueError(f"{name} must be at most {MAX_TEXT_LENGTH} characters")
    return value


def _optional_year(name: str, value: Any) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, but true/false is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    latest = date.today().year
    if not 1 <= value <= latest:
        raise ValueError(f"{name} must be between 1 and {latest}")
    return value


def _optional_isbn(name: str, value: Any) -> str | None:
    """Check an ISBN-10/ISBN-13 and its check digit; drop hyphens and spaces."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    isbn = _ISBN_SEPARATORS.sub("", value).upper()
    if not isbn:
        return None
    if not (_is_isbn10(isbn) or _is_isbn13(isbn)):
        raise ValueError(f"{name} must be a valid ISBN-10 or ISBN-13")
    return isbn


def _is_isbn10(isbn: str) -> bool:
    # Digits are weighted 10 down to 1; a final "X" stands for 10.
    if not _ISBN10.fullmatch(isbn):
        return False
    values = [10 if char == "X" else int(char) for char in isbn]
    return sum(w * v for w, v in zip(range(10, 0, -1), values, strict=True)) % 11 == 0


def _is_isbn13(isbn: str) -> bool:
    # Digits are weighted 1, 3, 1, 3, ...
    if not _ISBN13.fullmatch(isbn):
        return False
    return sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(isbn)) % 10 == 0


_CLEANERS = {
    "title": _required_text,
    "author": _required_text,
    "year": _optional_year,
    "isbn": _optional_isbn,
}
