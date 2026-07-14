"""Pydantic models for request validation and responses."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, description="Book title (required)")
    author: str = Field(..., min_length=1, description="Book author (required)")
    year: Optional[int] = Field(None, ge=0, le=9999)
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass


class Book(BookBase):
    id: int
