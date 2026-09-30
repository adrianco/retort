"""Plain data types shared by the validation, storage and HTTP layers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BookInput:
    """The client-supplied fields of a book, after validation."""

    title: str
    author: str
    year: int | None = None
    isbn: str | None = None


@dataclass(frozen=True)
class Book:
    """A stored book."""

    id: int
    title: str
    author: str
    year: int | None
    isbn: str | None
