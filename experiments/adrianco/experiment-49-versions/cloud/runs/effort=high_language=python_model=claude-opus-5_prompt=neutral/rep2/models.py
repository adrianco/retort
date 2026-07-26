"""Request/response schemas for the Book Collection API.

Validation rules (enforced by pydantic, surfaced to clients as HTTP 400):

* ``title`` and ``author`` are required, whitespace-trimmed and must not be blank.
* ``year`` is optional; when present it must be a plausible publication year.
* ``isbn`` is optional; when present it must look like an ISBN-10 or ISBN-13.
  Hyphens/spaces are stripped, so ``978-0-441-47812-5`` and ``9780441478125``
  are stored -- and de-duplicated -- identically.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: Earliest year we accept. Printing predates this, but a lower bound keeps
#: obvious typos (e.g. ``year=5``) out of the collection.
MIN_YEAR = 1000

#: Compact ISBN-10 (9 digits + digit/X check character) or ISBN-13 (13 digits).
#: Check digits are deliberately not verified -- format only.
_ISBN_RE = re.compile(r"(?:\d{9}[\dX]|\d{13})")

_TITLE_FIELD = dict(min_length=1, max_length=500, description="Book title (required)")
_AUTHOR_FIELD = dict(min_length=1, max_length=300, description="Author name (required)")


def max_year() -> int:
    """Upper bound for ``year``: next year, so forthcoming titles are allowed."""
    return date.today().year + 1


class _BookFields(BaseModel):
    """Shared config and field validators for the book payload models."""

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("year", check_fields=False)
    @classmethod
    def _validate_year(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if not MIN_YEAR <= value <= max_year():
            raise ValueError(f"year must be between {MIN_YEAR} and {max_year()}")
        return value

    @field_validator("isbn", check_fields=False)
    @classmethod
    def _validate_isbn(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        compact = re.sub(r"[\s-]", "", value).upper()
        if not compact:
            # A blank ISBN means "not provided" rather than a validation error.
            return None
        if not _ISBN_RE.fullmatch(compact):
            raise ValueError(
                "isbn must be a valid ISBN-10 or ISBN-13 "
                "(10 or 13 characters, hyphens and spaces allowed)"
            )
        return compact


class BookCreate(_BookFields):
    """Payload for ``POST /books``: the complete representation of a book."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "The Left Hand of Darkness",
                "author": "Ursula K. Le Guin",
                "year": 1969,
                "isbn": "978-0-441-47812-5",
            }
        },
    )

    title: str = Field(**_TITLE_FIELD)
    author: str = Field(**_AUTHOR_FIELD)
    year: Optional[int] = Field(default=None, description="Year of publication")
    isbn: Optional[str] = Field(default=None, description="ISBN-10 or ISBN-13")


class BookUpdate(BookCreate):
    """Payload for ``PUT /books/{id}``: a PUT replaces the whole resource."""


class BookPatch(_BookFields):
    """Payload for ``PATCH /books/{id}``: every field is optional.

    Omitted fields are left untouched. An explicit ``null`` clears ``year`` or
    ``isbn``; ``title`` and ``author`` may never be null because they are
    required columns.
    """

    title: Optional[str] = Field(default=None, **_TITLE_FIELD)
    author: Optional[str] = Field(default=None, **_AUTHOR_FIELD)
    year: Optional[int] = Field(default=None, description="Year of publication")
    isbn: Optional[str] = Field(default=None, description="ISBN-10 or ISBN-13")

    @model_validator(mode="before")
    @classmethod
    def _reject_explicit_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for name in ("title", "author"):
                if name in data and data[name] is None:
                    raise ValueError(f"{name} may not be null")
        return data

    @model_validator(mode="after")
    def _require_one_field(self) -> "BookPatch":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self

    def changes(self) -> dict[str, Any]:
        """Only the fields the client actually sent."""
        return self.model_dump(exclude_unset=True)


class Book(BaseModel):
    """A stored book, as returned by the API."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "The Left Hand of Darkness",
                "author": "Ursula K. Le Guin",
                "year": 1969,
                "isbn": "9780441478125",
            }
        }
    )

    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None


class FieldError(BaseModel):
    field: str
    message: str
    type: str


class ErrorResponse(BaseModel):
    """Uniform error body used for every non-2xx response."""

    detail: str
    errors: Optional[list[FieldError]] = None
