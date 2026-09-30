"""Validation and normalisation of book payloads sent by API clients."""

from __future__ import annotations

import unicodedata
from typing import Any, Callable, Mapping, Optional, TypedDict

MAX_TITLE_LENGTH = 255
MAX_AUTHOR_LENGTH = 255
MAX_ISBN_LENGTH = 32
# The range of a four-digit calendar year (ISO 8601, ``datetime.MINYEAR``/``MAXYEAR``).
MIN_YEAR = 1
MAX_YEAR = 9999


class BookFields(TypedDict):
    """The client-editable fields of a book."""

    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]


class ValidationError(Exception):
    """A payload failed validation; ``errors`` maps each offending field to a message."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("; ".join(f"{field}: {message}" for field, message in errors.items()))
        self.errors = errors


class _FieldError(ValueError):
    """Raised by the per-field parsers; the message is reported to the client."""


def _text(value: Any, max_length: int, *, required: bool) -> Optional[str]:
    """Trim ``value`` and check that it is a reasonable piece of text.

    A missing or blank value is an error when ``required``; otherwise it means
    "not set" and yields ``None``.
    """
    if value is None:
        if required:
            raise _FieldError("is required")
        return None
    if not isinstance(value, str):
        raise _FieldError("must be a string")
    text = value.strip()
    if not text:
        if required:
            raise _FieldError("must not be blank")
        return None
    if len(text) > max_length:
        raise _FieldError(f"must be at most {max_length} characters long")
    try:
        # JSON permits lone surrogates ("\ud800"); SQLite and our own response encoder cannot store them.
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise _FieldError("must be valid Unicode text") from None
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise _FieldError("must not contain control characters")
    return text


def _year(value: Any) -> Optional[int]:
    if value is None:
        return None
    # ``bool`` is a subclass of ``int``, but ``true`` is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        raise _FieldError("must be an integer")
    if not MIN_YEAR <= value <= MAX_YEAR:
        raise _FieldError(f"must be between {MIN_YEAR} and {MAX_YEAR}")
    return value


_PARSERS: tuple[tuple[str, Callable[[Any], Any]], ...] = (
    ("title", lambda value: _text(value, MAX_TITLE_LENGTH, required=True)),
    ("author", lambda value: _text(value, MAX_AUTHOR_LENGTH, required=True)),
    ("year", _year),
    ("isbn", lambda value: _text(value, MAX_ISBN_LENGTH, required=False)),
)


def validate_book(payload: Mapping[str, Any]) -> BookFields:
    """Return the cleaned book fields in ``payload`` or raise :class:`ValidationError`.

    ``title`` and ``author`` are required. ``year`` and ``isbn`` are optional:
    absent, ``null`` (and, for ``isbn``, blank) all mean "not set". Text is
    stripped of surrounding whitespace, and unknown keys (such as ``id``) are
    ignored. Every invalid field is reported, not just the first.
    """
    cleaned: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, parse in _PARSERS:
        try:
            cleaned[name] = parse(payload.get(name))
        except _FieldError as exc:
            errors[name] = str(exc)
    if errors:
        raise ValidationError(errors)
    return BookFields(**cleaned)
