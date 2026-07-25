"""Pydantic schemas for the Book Collection API."""

from pydantic import BaseModel, Field
from typing import Optional


class BookBase(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

    class Config:
        orm_mode = True


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

    class Config:
        orm_mode = True


class BookRead(BookBase):
    id: int
