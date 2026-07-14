"""FastAPI service for managing a book collection, backed by SQLite."""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

import database


def get_db_path() -> str:
    return os.environ.get("BOOKS_DB_PATH", database.DEFAULT_DB_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db(get_db_path())
    yield


app = FastAPI(title="Book Collection API", lifespan=lifespan)


class BookBase(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass


class Book(BookBase):
    id: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate, db_path: str = Depends(get_db_path)) -> dict:
    return database.create_book(db_path, book.title, book.author, book.year, book.isbn)


@app.get("/books", response_model=list[Book])
def list_books(
    author: Optional[str] = Query(default=None), db_path: str = Depends(get_db_path)
) -> list[dict]:
    return database.list_books(db_path, author)


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, db_path: str = Depends(get_db_path)) -> dict:
    book = database.get_book(db_path, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=Book)
def update_book(
    book_id: int, book: BookUpdate, db_path: str = Depends(get_db_path)
) -> dict:
    updated = database.update_book(
        db_path, book_id, book.title, book.author, book.year, book.isbn
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return updated


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db_path: str = Depends(get_db_path)) -> None:
    deleted = database.delete_book(db_path, book_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
