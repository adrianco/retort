"""Data types shared by the validation, storage and HTTP layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BookData:
    """Validated, client-supplied book fields (everything except the id)."""

    title: str
    author: str
    year: int | None = None
    isbn: str | None = None


@dataclass(frozen=True, slots=True)
class Book:
    """A book as stored in the collection."""

    id: int
    title: str
    author: str
    year: int | None = None
    isbn: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
