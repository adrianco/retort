"""Request and response models for books."""

import datetime
import re
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
)
from pydantic_core import PydanticCustomError

MAX_TEXT_LENGTH = 500
MAX_ISBN_LENGTH = 32

# Unicode category Cc: C0 controls, DEL and C1 controls.
_CONTROL_CHARACTERS = re.compile("[\x00-\x1f\x7f-\x9f]")


def _no_control_characters(value: str | None) -> str | None:
    # These have no place in a title, name or ISBN, and a NUL in particular
    # truncates the text for many consumers, SQLite's own length() included.
    if value is not None and _CONTROL_CHARACTERS.search(value):
        raise PydanticCustomError(
            "control_characters", "String should not contain control characters"
        )
    return value


def _not_in_future(year: int | None) -> int | None:
    # Checked on every request rather than fixed at import time, so the bound
    # stays correct in a process that keeps running into a new year.
    if year is not None and year > datetime.date.today().year:
        raise PydanticCustomError("year_in_future", "Year cannot be in the future")
    return year


def _blank_to_none(value: str | None) -> str | None:
    return value or None


RequiredText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=MAX_TEXT_LENGTH),
    AfterValidator(_no_control_characters),
]


class BookIn(BaseModel):
    """Body of ``POST /books`` and ``PUT /books/{id}``.

    Strings are trimmed, so a whitespace-only title or author counts as missing,
    and may not contain control characters. ``year`` must be a JSON integer (not
    a string or boolean). Unknown fields, including ``id``, are ignored.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    title: RequiredText
    author: RequiredText
    year: Annotated[StrictInt | None, Field(ge=1), AfterValidator(_not_in_future)] = None
    isbn: Annotated[
        str | None,
        Field(max_length=MAX_ISBN_LENGTH),
        AfterValidator(_no_control_characters),
        AfterValidator(_blank_to_none),
    ] = None


class Book(BaseModel):
    """A stored book, as returned by the API."""

    id: int
    title: str
    author: str
    year: int | None
    isbn: str | None
