"""Payload validation for book resources.

Reports *every* problem in one response rather than failing on the first one,
so a client can fix a whole form in a single round trip.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .errors import ValidationError

WRITABLE_FIELDS = ("title", "author", "year", "isbn")

# Accepted in a payload but ignored: they are server-owned. Echoing back a
# object fetched from GET /books/<id> is a normal read-modify-write flow and
# should not be punished with a 400.
SERVER_OWNED_FIELDS = frozenset({"id", "created_at", "updated_at"})

MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 255
MAX_ISBN_LENGTH = 64
MIN_YEAR = 1
FUTURE_YEAR_ALLOWANCE = 5  # forthcoming titles have a publication year ahead of now


def _max_year() -> int:
    # Computed per call so a long-lived process does not go stale on Dec 31.
    return datetime.now(timezone.utc).year + FUTURE_YEAR_ALLOWANCE


def _text_problem(value: str) -> str | None:
    """Describe text SQLite cannot store, else None.

    JSON permits escapes like ``\\ud800``, which Python decodes to an unpaired
    surrogate; binding one raises UnicodeEncodeError rather than sqlite3.Error,
    so without this check bad client input would surface as a 500.
    """
    if "\x00" in value:
        return "must not contain NUL bytes."
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return "must be valid UTF-8 text (unpaired surrogates are not allowed)."
    return None


def _clean_required_text(
    value: Any, field: str, max_length: int, errors: dict[str, str]
) -> str | None:
    if value is None:
        errors[field] = f"{field} is required and may not be null."
        return None
    if not isinstance(value, str):
        errors[field] = f"{field} must be a string."
        return None
    cleaned = value.strip()
    if not cleaned:
        errors[field] = f"{field} must not be empty."
        return None
    if len(cleaned) > max_length:
        errors[field] = f"{field} must be at most {max_length} characters."
        return None
    problem = _text_problem(cleaned)
    if problem:
        errors[field] = f"{field} {problem}"
        return None
    return cleaned


def _parse_plain_digits(value: str) -> int | None:
    """Parse a plain run of ASCII digits, else None.

    Deliberately narrower than ``int()``, which also accepts PEP 515 underscores
    (``"1_969"``), a leading sign (``"+1969"``) and non-ASCII decimals
    (``"٣"``) -- all silent misparses for a field like ``year``. It is also
    narrower than ``str.isdigit()``, which is True for characters ``int()``
    rejects outright (``"²"``, ``"፩"``) and so would raise ValueError.
    """
    stripped = value.strip()
    if stripped.isascii() and stripped.isdecimal():
        return int(stripped)
    return None


def _clean_year(value: Any, errors: dict[str, str]) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, so True would otherwise sneak through as 1.
    if isinstance(value, bool):
        errors["year"] = "year must be an integer."
        return None
    if isinstance(value, int):
        year = value
    elif isinstance(value, str):
        parsed = _parse_plain_digits(value)
        if parsed is None:
            errors["year"] = "year must be an integer."
            return None
        year = parsed
    else:
        errors["year"] = "year must be an integer."
        return None

    max_year = _max_year()
    if not MIN_YEAR <= year <= max_year:
        errors["year"] = f"year must be between {MIN_YEAR} and {max_year}."
        return None
    return year


def _clean_isbn(value: Any, errors: dict[str, str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "isbn must be a string."
        return None
    cleaned = value.strip()
    if not cleaned:
        # Storing "" would make a second blank ISBN collide with the UNIQUE
        # index, so an absent value is normalised to NULL.
        return None
    if len(cleaned) > MAX_ISBN_LENGTH:
        errors["isbn"] = f"isbn must be at most {MAX_ISBN_LENGTH} characters."
        return None
    problem = _text_problem(cleaned)
    if problem:
        errors["isbn"] = f"isbn {problem}"
        return None
    return cleaned


def _check_id(payload: dict[str, Any], expected_id: int, errors: dict[str, str]) -> None:
    """Flag an ``id`` in the body that contradicts the id in the URL."""
    if payload.get("id") is None:
        return
    body_id = payload["id"]
    if isinstance(body_id, str):
        body_id = _parse_plain_digits(body_id)  # None if unparseable -> mismatch
    # bool first: True == 1 would otherwise pass for book 1.
    if isinstance(body_id, bool) or body_id != expected_id:
        errors["id"] = f"id must match the id in the URL ({expected_id})."


def validate_book_payload(
    payload: Any, *, expected_id: int | None = None
) -> dict[str, Any]:
    """Validate a create/replace payload, returning cleaned column values.

    Args:
        payload: the decoded request body.
        expected_id: for a replace, the id from the URL. A contradicting ``id``
            in the body is collected alongside the field errors rather than
            short-circuiting them, so one response still reports every problem.

    Raises:
        ValidationError: if the payload is not an object or any field is bad.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    errors: dict[str, str] = {}

    if expected_id is not None:
        _check_id(payload, expected_id, errors)

    unknown = sorted(set(payload) - set(WRITABLE_FIELDS) - SERVER_OWNED_FIELDS)
    for field in unknown:
        errors[field] = (
            "Unknown field. Allowed fields are: " + ", ".join(WRITABLE_FIELDS) + "."
        )

    if "title" not in payload:
        errors["title"] = "title is required."
        title = None
    else:
        title = _clean_required_text(
            payload["title"], "title", MAX_TITLE_LENGTH, errors
        )

    if "author" not in payload:
        errors["author"] = "author is required."
        author = None
    else:
        author = _clean_required_text(
            payload["author"], "author", MAX_AUTHOR_LENGTH, errors
        )

    year = _clean_year(payload.get("year"), errors)
    isbn = _clean_isbn(payload.get("isbn"), errors)

    if errors:
        raise ValidationError("Request body failed validation.", fields=errors)

    return {"title": title, "author": author, "year": year, "isbn": isbn}
