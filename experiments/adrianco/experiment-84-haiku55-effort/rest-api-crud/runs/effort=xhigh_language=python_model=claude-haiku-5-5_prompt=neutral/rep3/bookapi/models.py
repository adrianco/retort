"""Domain objects shared by the validation, storage and HTTP layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BookFields:
    """The client-supplied, already-validated attributes of a book."""

    title: str
    author: str
    year: int | None = None
    isbn: str | None = None


@dataclass(frozen=True)
class Book(BookFields):
    """A stored book, identified by its database ID."""

    id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "isbn": self.isbn,
        }
