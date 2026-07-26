"""Request/response models and validation rules."""

from __future__ import annotations

import datetime as _dt
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Earliest plausible printed book; guards against typos like year=20.
MIN_YEAR = 1450
# Allow a little slack for forthcoming titles.
MAX_YEAR = _dt.date.today().year + 5

_ISBN_ALLOWED = re.compile(r"^[0-9Xx\-\s]+$")


class BookIn(BaseModel):
    """Payload accepted by POST /books and PUT /books/{id}."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=300)
    year: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    isbn: str | None = Field(default=None, max_length=20)

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v == "":
            # Treat an empty string as "not provided" so it does not collide
            # with the UNIQUE index on isbn.
            return None
        if not _ISBN_ALLOWED.match(v):
            raise ValueError("isbn may only contain digits, 'X', hyphens and spaces")
        digits = re.sub(r"[\s\-]", "", v)
        if len(digits) not in (10, 13):
            raise ValueError("isbn must have 10 or 13 characters excluding separators")
        return v


class Book(BookIn):
    """A stored book, including its server-assigned id."""

    id: int


class ErrorResponse(BaseModel):
    detail: str
