"""Plain data types shared by the validation, storage and HTTP layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BookData:
    """The client-supplied part of a book, after validation and normalisation."""

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
    year: int | None = None
    isbn: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """The JSON representation returned by the API."""
        return asdict(self)
