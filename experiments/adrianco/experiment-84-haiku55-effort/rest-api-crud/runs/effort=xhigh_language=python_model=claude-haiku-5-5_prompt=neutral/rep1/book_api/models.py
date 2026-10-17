"""Plain data objects shared by the validation, repository and HTTP layers."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BookFields:
    """The writable attributes of a book, after validation and normalisation."""

    title: str
    author: str
    year: int | None
    isbn: str | None


@dataclass(frozen=True)
class Book:
    """A stored book, including its database identifier."""

    id: int
    title: str
    author: str
    year: int | None
    isbn: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
