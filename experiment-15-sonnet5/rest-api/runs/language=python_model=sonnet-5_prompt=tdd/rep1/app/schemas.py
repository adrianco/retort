from typing import Optional

from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookUpdate(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None
