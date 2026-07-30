"""Input validation for book payloads.

`validate_book_payload` never raises on bad user input: it returns the
cleaned field values plus a mapping of field name -> error message so the
caller can emit a single 400 response describing everything that is wrong.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

MAX_TITLE_LEN = 500
MAX_AUTHOR_LEN = 255
MAX_ISBN_LEN = 20

MIN_YEAR = 1
#: Publication years may legitimately be slightly in the future (pre-orders).
MAX_YEAR_SLACK = 1

_ISBN_ALLOWED = set("0123456789Xx- ")

#: Fields a client may supply. Anything else in the body is ignored.
FIELDS = ("title", "author", "year", "isbn")


def _max_year() -> int:
    return _dt.date.today().year + MAX_YEAR_SLACK


def _validate_text(value: Any, field: str, max_len: int) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, f"'{field}' must be a string"
    cleaned = value.strip()
    if not cleaned:
        return None, f"'{field}' must not be empty"
    if len(cleaned) > max_len:
        return None, f"'{field}' must be at most {max_len} characters"
    return cleaned, None


def _validate_year(value: Any) -> tuple[int | None, str | None]:
    if value is None:
        return None, None
    # bool is a subclass of int; True would otherwise become year 1.
    if isinstance(value, bool):
        return None, "'year' must be an integer"
    if isinstance(value, int):
        year = value
    elif isinstance(value, str) and value.strip().lstrip("-").isdigit():
        year = int(value.strip())
    else:
        return None, "'year' must be an integer"
    if not MIN_YEAR <= year <= _max_year():
        return None, f"'year' must be between {MIN_YEAR} and {_max_year()}"
    return year, None


def _validate_isbn(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "'isbn' must be a string"
    cleaned = value.strip()
    if not cleaned:
        # An explicit empty string is treated as "no ISBN".
        return None, None
    if len(cleaned) > MAX_ISBN_LEN:
        return None, f"'isbn' must be at most {MAX_ISBN_LEN} characters"
    if not set(cleaned) <= _ISBN_ALLOWED:
        return None, "'isbn' may only contain digits, 'X', hyphens and spaces"
    return cleaned, None


def validate_book_payload(
    payload: Any, *, partial: bool = False
) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate a create/update payload.

    Args:
        payload: The decoded JSON body.
        partial: When True (PATCH), omitted fields are left out of the result
            instead of being reported as missing.

    Returns:
        ``(values, errors)``. ``values`` only contains keys the client
        supplied (or, for a non-partial payload, every field). ``errors`` is
        empty when the payload is valid.
    """
    if not isinstance(payload, dict):
        return {}, {"_body": "Request body must be a JSON object"}

    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for field, max_len in (("title", MAX_TITLE_LEN), ("author", MAX_AUTHOR_LEN)):
        if field not in payload:
            # title and author are required; on PATCH they may be omitted.
            if not partial:
                errors[field] = f"'{field}' is required"
            continue
        cleaned, error = _validate_text(payload[field], field, max_len)
        if error:
            errors[field] = error
        else:
            values[field] = cleaned

    for field, validator in (("year", _validate_year), ("isbn", _validate_isbn)):
        if field not in payload:
            # year and isbn are optional. A full update (PUT) replaces the
            # resource, so an omitted optional field is cleared.
            if not partial:
                values[field] = None
            continue
        cleaned, error = validator(payload[field])
        if error:
            errors[field] = error
        else:
            values[field] = cleaned

    if partial and not values and not errors:
        errors["_body"] = "At least one field must be supplied"

    return values, errors
