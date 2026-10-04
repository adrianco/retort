"""Validation of book payloads received from clients."""

MIN_YEAR = -9999
MAX_YEAR = 9999


class ValidationError(Exception):
    """Raised with a ``{field: message}`` mapping describing what is wrong."""

    def __init__(self, errors):
        super().__init__("Validation failed")
        self.errors = errors


def _is_storable(text):
    # JSON can carry lone surrogates ("\ud800"), which SQLite cannot store.
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _required_text(payload, field, errors):
    value = payload.get(field)
    if value is None:
        errors[field] = f"{field} is required"
    elif not isinstance(value, str):
        errors[field] = f"{field} must be a string"
    elif not value.strip():
        errors[field] = f"{field} must not be empty"
    elif not _is_storable(value):
        errors[field] = f"{field} contains invalid characters"
    else:
        return value.strip()
    return None


def _optional_year(payload, errors):
    value = payload.get("year")
    if value is None:
        return None
    # bool is a subclass of int, but `true` is not a year.
    if isinstance(value, bool) or not isinstance(value, int):
        errors["year"] = "year must be an integer"
    elif not MIN_YEAR <= value <= MAX_YEAR:
        errors["year"] = f"year must be between {MIN_YEAR} and {MAX_YEAR}"
    else:
        return value
    return None


def _optional_isbn(payload, errors):
    value = payload.get("isbn")
    if value is None:
        return None
    if not isinstance(value, str):
        errors["isbn"] = "isbn must be a string"
    elif not _is_storable(value):
        errors["isbn"] = "isbn contains invalid characters"
    else:
        return value.strip() or None
    return None


def validate_book(payload):
    """Return a clean ``{title, author, year, isbn}`` dict from a JSON payload.

    ``title`` and ``author`` are required; ``year`` and ``isbn`` are optional
    and default to ``None``. Unknown fields (including ``id``) are ignored so
    that clients can send back an object they previously fetched.

    Raises ``ValidationError`` listing every invalid field.
    """
    if not isinstance(payload, dict):
        raise ValidationError({"body": "request body must be a JSON object"})

    errors = {}
    book = {
        "title": _required_text(payload, "title", errors),
        "author": _required_text(payload, "author", errors),
        "year": _optional_year(payload, errors),
        "isbn": _optional_isbn(payload, errors),
    }
    if errors:
        raise ValidationError(errors)
    return book
