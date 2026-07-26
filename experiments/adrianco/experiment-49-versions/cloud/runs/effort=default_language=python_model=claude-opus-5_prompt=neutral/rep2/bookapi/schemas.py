"""Request and response models, including input validation rules."""

from __future__ import annotations

import re
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

MIN_YEAR = 1
MAX_YEAR = 2100

# ISBN-10 (last character may be the check digit "X") or ISBN-13, separators removed.
_ISBN_RE = re.compile(r"^(?:\d{9}[\dX]|\d{13})$")

Title = Annotated[str, Field(min_length=1, max_length=500, examples=["Dune"])]
Author = Annotated[str, Field(min_length=1, max_length=255, examples=["Frank Herbert"])]
Year = Annotated[Optional[int], Field(default=None, ge=MIN_YEAR, le=MAX_YEAR, examples=[1965])]
Isbn = Annotated[Optional[str], Field(default=None, examples=["978-0441013593"])]


class BookInput(BaseModel):
    """Fields accepted when creating or replacing a book."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Title
    author: Author
    year: Year
    isbn: Isbn

    @field_validator("title", "author")
    @classmethod
    def _reject_blank(cls, value: str, info) -> str:
        # str_strip_whitespace runs first, so a whitespace-only value arrives empty.
        if not value:
            raise ValueError(f"{info.field_name} must not be empty")
        return value

    @field_validator("isbn")
    @classmethod
    def _normalise_isbn(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalised = re.sub(r"[\s-]", "", value).upper()
        if not normalised:
            return None
        if not _ISBN_RE.match(normalised):
            raise ValueError("isbn must be a 10 or 13 character ISBN, e.g. 978-0441013593")
        return normalised


class BookCreate(BookInput):
    """Body of POST /books."""


class BookReplace(BookInput):
    """Body of PUT /books/{id}: a full replacement, so optional fields reset to null."""


class Book(BaseModel):
    """A stored book, as returned by the API."""

    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None
    created_at: str
    updated_at: str


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    """Every non-2xx response from this API uses this shape."""

    error: str
    message: str
    details: list[ErrorDetail] = []


class HealthResponse(BaseModel):
    status: str
    database: str
