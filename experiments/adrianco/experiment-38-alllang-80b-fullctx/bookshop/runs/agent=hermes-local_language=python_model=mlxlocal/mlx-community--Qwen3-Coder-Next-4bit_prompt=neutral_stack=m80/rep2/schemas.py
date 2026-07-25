"""Pydantic schemas for book requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional


class BookCreate(BaseModel):
    """Schema for creating a new book."""
    title: str = Field(..., min_length=1, description="Book title (required)")
    author: str = Field(..., min_length=1, description="Author name (required)")
    year: Optional[int] = Field(None, ge=1000, le=9999, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN number")


class BookUpdate(BaseModel):
    """Schema for updating a book."""
    title: Optional[str] = Field(default=None, min_length=1, description="Book title")
    author: Optional[str] = Field(default=None, min_length=1, description="Author name")
    year: Optional[int] = Field(default=None, ge=1000, le=9999, description="Publication year")
    isbn: Optional[str] = Field(default=None, description="ISBN number")


class BookResponse(BaseModel):
    """Schema for book response."""
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]


class BooksListResponse(BaseModel):
    """Schema for list of books response."""
    books: list[BookResponse]
    total: int


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str = "healthy"
    database: str = "connected"
