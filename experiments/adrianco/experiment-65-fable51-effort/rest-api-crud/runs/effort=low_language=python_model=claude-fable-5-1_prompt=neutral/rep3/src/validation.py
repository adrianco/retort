"""Input validation for book payloads."""
from typing import Any


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


def validate_book(payload: Any) -> dict:
    """Validate and normalise a book payload. Raises ValidationError."""
    if not isinstance(payload, dict):
        raise ValidationError({"body": "must be a JSON object"})
    errors: dict[str, str] = {}

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        errors["title"] = "is required and must be a non-empty string"
    author = payload.get("author")
    if not isinstance(author, str) or not author.strip():
        errors["author"] = "is required and must be a non-empty string"

    year = payload.get("year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)
                             or year < 0 or year > 9999):
        errors["year"] = "must be an integer between 0 and 9999"

    isbn = payload.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str):
            errors["isbn"] = "must be a string"
        else:
            digits = isbn.replace("-", "").replace(" ", "")
            if not (digits.isalnum() and len(digits) in (10, 13)):
                errors["isbn"] = "must be a 10 or 13 character ISBN"

    if errors:
        raise ValidationError(errors)
    return {"title": title.strip(), "author": author.strip(), "year": year, "isbn": isbn}
