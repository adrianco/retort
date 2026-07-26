"""Request-payload validation.

Validation is deliberately kept free of Flask imports so it can be unit-tested
on its own.  Every validator collects *all* problems it finds rather than
bailing out at the first one, so a client gets the full picture in one round
trip.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 255
MAX_ISBN_LENGTH = 32
MIN_YEAR = 1
MAX_YEAR = 9999

#: Fields a client is allowed to supply.  Anything else (``id``, timestamps,
#: typos) is ignored rather than rejected.
BOOK_FIELDS: Sequence[str] = ("title", "author", "year", "isbn")

_ISBN_SEPARATORS = re.compile(r"[\s\-]")
_ISBN_10 = re.compile(r"^\d{9}[\dXx]$")
_ISBN_13 = re.compile(r"^\d{13}$")
_INT_STRING = re.compile(r"^[+-]?\d+$")


class ValidationError(Exception):
    """Raised when a request payload cannot be turned into a valid book."""

    def __init__(self, errors: Sequence[Dict[str, str]]):
        self.errors: List[Dict[str, str]] = list(errors)
        super().__init__(self.message)

    @property
    def messages(self) -> List[str]:
        return [error["message"] for error in self.errors]

    @property
    def message(self) -> str:
        return "; ".join(self.messages) or "Validation failed"


def _err(field: Optional[str], message: str) -> Dict[str, str]:
    error = {"message": message}
    if field is not None:
        error["field"] = field
    return error


def _require_object(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError(
            [_err(None, "Request body must be a JSON object")]
        )
    return payload


def _validate_text(
    value: Any, field: str, max_length: int, errors: List[Dict[str, str]]
) -> Optional[str]:
    """Validate a required, non-empty string field and return it trimmed."""
    if value is None:
        errors.append(_err(field, f"'{field}' is required"))
        return None
    if isinstance(value, bool) or not isinstance(value, str):
        errors.append(_err(field, f"'{field}' must be a string"))
        return None

    cleaned = value.strip()
    if not cleaned:
        errors.append(_err(field, f"'{field}' must not be empty"))
        return None
    if len(cleaned) > max_length:
        errors.append(
            _err(field, f"'{field}' must be at most {max_length} characters")
        )
        return None
    return cleaned


def _validate_year(value: Any, errors: List[Dict[str, str]]) -> Optional[int]:
    """Validate the optional ``year`` field.

    Accepts a JSON number or a numeric string; ``None``/``""`` mean "unset".
    """
    if value is None:
        return None
    if isinstance(value, bool):
        errors.append(_err("year", "'year' must be an integer"))
        return None

    if isinstance(value, int):
        year = value
    elif isinstance(value, float):
        if not value.is_integer():
            errors.append(_err("year", "'year' must be a whole number"))
            return None
        year = int(value)
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if not _INT_STRING.match(candidate):
            errors.append(_err("year", "'year' must be an integer"))
            return None
        year = int(candidate)
    else:
        errors.append(_err("year", "'year' must be an integer"))
        return None

    if not MIN_YEAR <= year <= MAX_YEAR:
        errors.append(
            _err("year", f"'year' must be between {MIN_YEAR} and {MAX_YEAR}")
        )
        return None
    return year


def _validate_isbn(value: Any, errors: List[Dict[str, str]]) -> Optional[str]:
    """Validate the optional ``isbn`` field.

    The shape is checked (10 or 13 digits, optional ``X`` check character on
    ISBN-10, hyphens and spaces allowed as separators) but the value is stored
    exactly as the client wrote it so round-trips are lossless.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        errors.append(_err("isbn", "'isbn' must be a string"))
        return None

    raw = str(value).strip()
    if not raw:
        return None
    if len(raw) > MAX_ISBN_LENGTH:
        errors.append(
            _err("isbn", f"'isbn' must be at most {MAX_ISBN_LENGTH} characters")
        )
        return None

    compact = _ISBN_SEPARATORS.sub("", raw)
    if not (_ISBN_10.match(compact) or _ISBN_13.match(compact)):
        errors.append(
            _err("isbn", "'isbn' must be a 10- or 13-digit ISBN")
        )
        return None
    return raw


def _validate_field(
    field: str, value: Any, errors: List[Dict[str, str]]
) -> Any:
    if field == "title":
        return _validate_text(value, "title", MAX_TITLE_LENGTH, errors)
    if field == "author":
        return _validate_text(value, "author", MAX_AUTHOR_LENGTH, errors)
    if field == "year":
        return _validate_year(value, errors)
    if field == "isbn":
        return _validate_isbn(value, errors)
    raise AssertionError(f"unknown field {field!r}")  # pragma: no cover


def validate_new_book(payload: Any) -> Dict[str, Any]:
    """Validate a ``POST /books`` payload.

    ``title`` and ``author`` are required; ``year`` and ``isbn`` are optional.
    """
    payload = _require_object(payload)
    errors: List[Dict[str, str]] = []
    book = {
        field: _validate_field(field, payload.get(field), errors)
        for field in BOOK_FIELDS
    }
    if errors:
        raise ValidationError(errors)
    return book


def validate_book_update(payload: Any) -> Dict[str, Any]:
    """Validate a ``PUT``/``PATCH`` payload.

    Only the supplied fields are validated and returned, so a client may send
    either a complete representation or just the parts it wants to change.
    Sending ``null`` for ``year``/``isbn`` explicitly clears them.
    """
    payload = _require_object(payload)
    provided = [field for field in BOOK_FIELDS if field in payload]
    if not provided:
        raise ValidationError(
            [
                _err(
                    None,
                    "Request body must contain at least one of: "
                    + ", ".join(BOOK_FIELDS),
                )
            ]
        )

    errors: List[Dict[str, str]] = []
    changes = {
        field: _validate_field(field, payload[field], errors)
        for field in provided
    }
    if errors:
        raise ValidationError(errors)
    return changes


def validate_positive_int(
    name: str, raw: str, minimum: int = 0, maximum: Optional[int] = None
) -> int:
    """Validate an integer query-string parameter."""
    candidate = raw.strip()
    if not _INT_STRING.match(candidate):
        raise ValidationError([_err(name, f"'{name}' must be an integer")])

    value = int(candidate)
    if value < minimum:
        raise ValidationError(
            [_err(name, f"'{name}' must be greater than or equal to {minimum}")]
        )
    if maximum is not None and value > maximum:
        raise ValidationError(
            [_err(name, f"'{name}' must be less than or equal to {maximum}")]
        )
    return value
