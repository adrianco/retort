"""The domain model of the service."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Book:
    """A single book in the collection."""

    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Book":
        return cls(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            year=row["year"],
            isbn=row["isbn"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return the JSON representation sent to clients."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "isbn": self.isbn,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
