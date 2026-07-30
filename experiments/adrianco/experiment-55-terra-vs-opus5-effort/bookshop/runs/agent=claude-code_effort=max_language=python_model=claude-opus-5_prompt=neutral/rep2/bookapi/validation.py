"""Request payload and query-string validation.

The validators return normalised values (trimmed strings, coerced integers) so
that everything downstream - the repository and the JSON responses - works with
clean data only.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .errors import ValidationError

MAX_TITLE_LENGTH = 255
MAX_AUTHOR_LENGTH = 255
MAX_ISBN_LENGTH = 32
MIN_YEAR = -4000
#: How far into the future a publication year may reasonably be announced.
FUTURE_YEAR_ALLOWANCE = 10

#: Largest value SQLite can store in an INTEGER column.  Anything bigger raises
#: OverflowError at bind time, so it has to be rejected during validation.
SQLITE_MAX_INT = 2**63 - 1

#: Fields a client may set.
WRITABLE_FIELDS = ("title", "author", "year", "isbn")
#: Server-managed fields; accepted and ignored so a GET response can be edited
#: and sent straight back with PUT.
READ_ONLY_FIELDS = ("id", "created_at", "updated_at")

SORTABLE_FIELDS = ("id", "title", "author", "year", "created_at", "updated_at")
MAX_LIMIT = 1000

#: C0/C1 control characters.  ``str.strip()`` removes them only at the ends, and
#: SQLite's ``trim()``/``length()`` disagree about embedded NULs, so a title of
#: "\x00" would slip past both the validator and the table's CHECK constraint.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")

#: ASCII-only integer literal.  ``int()`` alone would also accept "1_9_5_8" and
#: non-ASCII digits such as "١٩٥٨".
_INTEGER = re.compile(r"[+-]?[0-9]+")


class _FieldError(Exception):
    """Internal marker carrying the reason a single field was rejected."""


def max_year() -> int:
    return datetime.now(timezone.utc).year + FUTURE_YEAR_ALLOWANCE


def _parse_int(text: str) -> int:
    if not _INTEGER.fullmatch(text.strip()):
        raise _FieldError("must be an integer")
    return int(text)


def _clean_text(value: Any, *, max_length: int) -> str:
    if value is None:
        raise _FieldError("this field is required")
    if not isinstance(value, str):
        raise _FieldError("must be a string")
    text = value.strip()
    if not text:
        raise _FieldError("must not be empty")
    if _CONTROL_CHARS.search(text):
        raise _FieldError("must not contain control characters")
    if len(text) > max_length:
        raise _FieldError(f"must be at most {max_length} characters")
    return text


def _clean_year(value: Any) -> int | None:
    if value is None:
        return None
    # bool is a subclass of int, but True is not a publication year.
    if isinstance(value, bool):
        raise _FieldError("must be an integer")
    if isinstance(value, int):
        year = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise _FieldError("must be a whole number")
        year = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        year = _parse_int(text)
    else:
        raise _FieldError("must be an integer")

    upper = max_year()
    if not MIN_YEAR <= year <= upper:
        raise _FieldError(f"must be between {MIN_YEAR} and {upper}")
    return year


def _clean_isbn(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _FieldError("must be a string")
    # Collapse internal runs of whitespace so "978 3 16" and "978  3 16" match.
    text = " ".join(value.split())
    if not text:
        return None
    if _CONTROL_CHARS.search(text):
        raise _FieldError("must not contain control characters")
    if len(text) > MAX_ISBN_LENGTH:
        raise _FieldError(f"must be at most {MAX_ISBN_LENGTH} characters")
    return text


def validate_book_payload(payload: Any, *, partial: bool = False) -> dict[str, Any]:
    """Validate a create/update body and return the normalised fields.

    With ``partial=False`` (POST and PUT) the result always contains all four
    writable fields, so a PUT genuinely replaces the resource: any field the
    client omits is reset to ``NULL``.  With ``partial=True`` (PATCH) only the
    supplied fields are returned.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    errors: dict[str, str] = {}
    cleaned: dict[str, Any] = {}

    known = set(WRITABLE_FIELDS) | set(READ_ONLY_FIELDS)
    for field in sorted(set(payload) - known):
        errors[field] = "unknown field"

    cleaners = {
        "title": lambda v: _clean_text(v, max_length=MAX_TITLE_LENGTH),
        "author": lambda v: _clean_text(v, max_length=MAX_AUTHOR_LENGTH),
        "year": _clean_year,
        "isbn": _clean_isbn,
    }
    required = {"title", "author"}

    for field, cleaner in cleaners.items():
        if field not in payload:
            if not partial:
                if field in required:
                    errors[field] = "this field is required"
                else:
                    # Absent optional field on a full replacement clears it.
                    cleaned[field] = None
            continue
        try:
            cleaned[field] = cleaner(payload[field])
        except _FieldError as exc:
            errors[field] = str(exc)

    if errors:
        raise ValidationError("Request validation failed.", details=errors)

    if partial and not cleaned:
        raise ValidationError(
            "Request body must contain at least one field to update.",
            details={"body": f"expected one of: {', '.join(WRITABLE_FIELDS)}"},
        )

    return cleaned


def _clean_bounded_int(raw: str, *, field: str, minimum: int, maximum: int) -> int:
    try:
        value = _parse_int(raw)
    except _FieldError as exc:
        raise ValidationError(
            "Invalid query parameters.", details={field: str(exc)}
        ) from None
    if not minimum <= value <= maximum:
        raise ValidationError(
            "Invalid query parameters.",
            details={field: f"must be between {minimum} and {maximum}"},
        )
    return value


def validate_list_query(args: Mapping[str, str]) -> dict[str, Any]:
    """Validate the query string of ``GET /books``."""
    query: dict[str, Any] = {
        "author": None,
        "title": None,
        "year": None,
        "sort": "id",
        "descending": False,
        "limit": None,
        "offset": 0,
    }

    for field in ("author", "title"):
        raw = args.get(field)
        if raw is not None and raw.strip():
            query[field] = raw.strip()

    raw_year = args.get("year")
    if raw_year is not None and raw_year.strip():
        try:
            query["year"] = _clean_year(raw_year)
        except _FieldError as exc:
            raise ValidationError(
                "Invalid query parameters.", details={"year": str(exc)}
            ) from None

    raw_sort = args.get("sort")
    if raw_sort is not None and raw_sort.strip():
        sort = raw_sort.strip()
        descending = sort.startswith("-")
        # Strip one optional direction prefix, so "--title" stays invalid.
        sort = sort[1:] if sort[:1] in ("-", "+") else sort
        if sort not in SORTABLE_FIELDS:
            raise ValidationError(
                "Invalid query parameters.",
                details={"sort": f"must be one of: {', '.join(SORTABLE_FIELDS)}"},
            )
        query["sort"] = sort
        query["descending"] = descending

    raw_limit = args.get("limit")
    if raw_limit is not None and raw_limit.strip():
        query["limit"] = _clean_bounded_int(
            raw_limit, field="limit", minimum=1, maximum=MAX_LIMIT
        )

    raw_offset = args.get("offset")
    if raw_offset is not None and raw_offset.strip():
        query["offset"] = _clean_bounded_int(
            raw_offset, field="offset", minimum=0, maximum=SQLITE_MAX_INT
        )

    return query
