"""Input validation for request bodies and query strings.

The validators collect *every* problem they find and raise a single
:class:`~book_api.errors.ValidationError` carrying a field -> message mapping,
so a client can fix a whole payload in one round trip.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional, Tuple

from .errors import ValidationError
from .repository import SORTABLE_FIELDS, SQLITE_INT_MAX, SQLITE_INT_MIN
from .utils import current_year

MAX_TITLE_LENGTH = 512
MAX_AUTHOR_LENGTH = 256
MAX_ISBN_LENGTH = 32
MAX_QUERY_LENGTH = 256
#: Earliest accepted publication year.  Books older than this exist, but a
#: value below it is far more likely to be a typo than a real edition date.
MIN_YEAR = 1

#: Fields a client may send.  Anything else is ignored, which lets a client
#: round-trip a book it just read (``id``/``created_at``/...) straight back.
WRITABLE_FIELDS = ("title", "author", "year", "isbn")

#: A signed 64-bit integer never needs more than 19 digits.  Longer runs are
#: rejected outright: CPython refuses to convert strings of more than 4300
#: digits at all, and nothing in that range could pass the bounds checks anyway.
MAX_INTEGER_DIGITS = 19

# ``\d`` also matches Arabic-Indic and fullwidth digits, which int() happily
# converts; every pattern here is deliberately restricted to ASCII digits.
_INTEGER_RE = re.compile(r"^[+-]?[0-9]+$")
# ASCII hyphen, the Unicode dash block and the minus sign are all accepted as
# ISBN group separators, alongside any whitespace.
_ISBN_SEPARATORS_RE = re.compile(r"[\s\-‐-―−]")
_ISBN10_RE = re.compile(r"^[0-9]{9}[0-9X]$")
_ISBN13_RE = re.compile(r"^[0-9]{13}$")


# ----------------------------------------------------------------------
# ISBN helpers
# ----------------------------------------------------------------------
def normalize_isbn(value: str) -> str:
    """Strip separators and upper-case the check digit of an ISBN."""
    return _ISBN_SEPARATORS_RE.sub("", value).upper()


def has_isbn_shape(normalized: str) -> bool:
    """True when the value has 10 or 13 digits (``X`` allowed as ISBN-10 check digit)."""
    return bool(_ISBN10_RE.match(normalized) or _ISBN13_RE.match(normalized))


def has_valid_isbn_checksum(normalized: str) -> bool:
    """Validate the ISBN-10 (mod 11) or ISBN-13 (mod 10) check digit."""
    if _ISBN10_RE.match(normalized):
        total = sum(
            (10 - index) * (10 if char == "X" else int(char))
            for index, char in enumerate(normalized)
        )
        return total % 11 == 0
    if _ISBN13_RE.match(normalized):
        total = sum(
            int(char) * (1 if index % 2 == 0 else 3)
            for index, char in enumerate(normalized)
        )
        return total % 10 == 0
    return False


# ----------------------------------------------------------------------
# Request body
# ----------------------------------------------------------------------
def _parse_string(value: Any, field: str, max_length: int, errors: Dict[str, str]) -> Optional[str]:
    if not isinstance(value, str):
        errors[field] = "Must be a string."
        return None
    stripped = value.strip()
    if not stripped:
        errors[field] = "Must not be empty."
        return None
    if len(stripped) > max_length:
        errors[field] = "Must be at most {} characters long.".format(max_length)
        return None
    if "\x00" in stripped:
        errors[field] = "Must not contain null bytes."
        return None
    try:
        # JSON permits unpaired surrogates; SQLite cannot store them.
        stripped.encode("utf-8")
    except UnicodeEncodeError:
        errors[field] = "Must be valid UTF-8 text."
        return None
    return stripped


def _parse_year(value: Any, errors: Dict[str, str]) -> Optional[int]:
    if value is None:
        return None
    year: Optional[int] = None
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        errors["year"] = "Must be an integer."
        return None
    if isinstance(value, int):
        year = value
    elif isinstance(value, float):
        if not value.is_integer():
            errors["year"] = "Must be a whole number."
            return None
        year = int(value)
    elif isinstance(value, str):
        candidate = value.strip()
        if not _INTEGER_RE.match(candidate):
            errors["year"] = "Must be an integer."
            return None
        if len(candidate.lstrip("+-")) > MAX_INTEGER_DIGITS:
            errors["year"] = "Must be between {} and {}.".format(MIN_YEAR, current_year() + 1)
            return None
        year = int(candidate)
    else:
        errors["year"] = "Must be an integer."
        return None

    maximum = current_year() + 1
    if not MIN_YEAR <= year <= maximum:
        errors["year"] = "Must be between {} and {}.".format(MIN_YEAR, maximum)
        return None
    return year


def _parse_isbn(value: Any, strict_checksum: bool, errors: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(display value, normalized value)`` for an ISBN."""
    if value is None:
        return None, None
    if not isinstance(value, str):
        errors["isbn"] = "Must be a string."
        return None, None
    raw = value.strip()
    if not raw:
        return None, None
    if len(raw) > MAX_ISBN_LENGTH:
        errors["isbn"] = "Must be at most {} characters long.".format(MAX_ISBN_LENGTH)
        return None, None
    normalized = normalize_isbn(raw)
    if not has_isbn_shape(normalized):
        errors["isbn"] = "Must be a valid ISBN-10 or ISBN-13 (10 or 13 digits, hyphens optional)."
        return None, None
    if strict_checksum and not has_valid_isbn_checksum(normalized):
        errors["isbn"] = "The ISBN check digit is invalid."
        return None, None
    return raw, normalized


def parse_book_payload(
    data: Any,
    *,
    partial: bool = False,
    strict_isbn_checksum: bool = False,
) -> Dict[str, Any]:
    """Validate a book payload and return the column values to persist.

    Args:
        data: The decoded JSON body.
        partial: When true (``PATCH``) absent fields are simply left out of the
            result; when false (``POST``/``PUT``) ``title`` and ``author`` are
            required and absent optional fields are reset to ``None``.
        strict_isbn_checksum: Also verify the ISBN check digit.

    Raises:
        ValidationError: If the payload is not a JSON object or any field is
            rejected.  ``details`` maps each bad field to a message.
    """
    if not isinstance(data, dict):
        raise ValidationError(
            "The request body must be a JSON object.",
            details={"body": "Expected a JSON object such as {\"title\": \"...\", \"author\": \"...\"}."},
        )

    errors: Dict[str, str] = {}
    fields: Dict[str, Any] = {}

    for field, max_length in (("title", MAX_TITLE_LENGTH), ("author", MAX_AUTHOR_LENGTH)):
        if field in data:
            parsed = _parse_string(data[field], field, max_length, errors)
            if parsed is not None:
                fields[field] = parsed
        elif not partial:
            errors[field] = "This field is required."

    if "year" in data:
        year = _parse_year(data["year"], errors)
        if "year" not in errors:
            fields["year"] = year
    elif not partial:
        fields["year"] = None

    if "isbn" in data:
        isbn, normalized = _parse_isbn(data["isbn"], strict_isbn_checksum, errors)
        if "isbn" not in errors:
            fields["isbn"] = isbn
            fields["isbn_normalized"] = normalized
    elif not partial:
        fields["isbn"] = None
        fields["isbn_normalized"] = None

    if errors:
        raise ValidationError("The request payload failed validation.", details=errors)

    if partial and not fields:
        raise ValidationError(
            "No updatable fields were supplied.",
            details={"body": "Provide at least one of: {}.".format(", ".join(WRITABLE_FIELDS))},
        )

    return fields


# ----------------------------------------------------------------------
# Query string
# ----------------------------------------------------------------------
def _parse_int_in_range(
    raw: str, field: str, minimum: int, maximum: int, errors: Dict[str, str]
) -> Optional[int]:
    candidate = raw.strip()
    if not _INTEGER_RE.match(candidate):
        errors[field] = "Must be an integer."
        return None
    if len(candidate.lstrip("+-")) > MAX_INTEGER_DIGITS:
        # Too long to be in range, and too long for int() to convert at all.
        errors[field] = (
            "Must be greater than or equal to {}.".format(minimum)
            if candidate.startswith("-")
            else "Must be at most {}.".format(maximum)
        )
        return None
    value = int(candidate)
    if value < minimum:
        errors[field] = "Must be greater than or equal to {}.".format(minimum)
        return None
    if value > maximum:
        errors[field] = "Must be at most {}.".format(maximum)
        return None
    return value


def parse_list_query(args: Mapping[str, str], *, max_limit: int) -> Dict[str, Any]:
    """Validate the query string of ``GET /books``.

    Recognised parameters: ``author`` (case-insensitive exact match), ``year``,
    ``q`` (case-insensitive substring of title or author), ``sort``, ``limit``
    and ``offset``.  Blank values are treated as "not supplied".
    """
    errors: Dict[str, str] = {}
    result: Dict[str, Any] = {
        "author": None,
        "year": None,
        "query": None,
        "sort": ("id", "ASC"),
        "limit": None,
        "offset": 0,
    }

    author = (args.get("author") or "").strip()
    if author:
        if len(author) > MAX_AUTHOR_LENGTH:
            errors["author"] = "Must be at most {} characters long.".format(MAX_AUTHOR_LENGTH)
        else:
            result["author"] = author

    raw_year = (args.get("year") or "").strip()
    if raw_year:
        year = _parse_int_in_range(raw_year, "year", SQLITE_INT_MIN, SQLITE_INT_MAX, errors)
        if year is not None:
            result["year"] = year

    query = (args.get("q") or "").strip()
    if query:
        if len(query) > MAX_QUERY_LENGTH:
            errors["q"] = "Must be at most {} characters long.".format(MAX_QUERY_LENGTH)
        else:
            result["query"] = query

    raw_sort = (args.get("sort") or "").strip()
    if raw_sort:
        descending = raw_sort.startswith("-")
        column = raw_sort[1:] if descending else raw_sort
        if column not in SORTABLE_FIELDS:
            errors["sort"] = "Must be one of: {} (prefix with '-' to sort descending).".format(
                ", ".join(SORTABLE_FIELDS)
            )
        else:
            result["sort"] = (column, "DESC" if descending else "ASC")

    raw_limit = (args.get("limit") or "").strip()
    if raw_limit:
        limit = _parse_int_in_range(raw_limit, "limit", 1, max_limit, errors)
        if limit is not None:
            result["limit"] = limit

    raw_offset = (args.get("offset") or "").strip()
    if raw_offset:
        offset = _parse_int_in_range(raw_offset, "offset", 0, SQLITE_INT_MAX, errors)
        if offset is not None:
            result["offset"] = offset

    if errors:
        raise ValidationError("The query string failed validation.", details=errors)

    return result
