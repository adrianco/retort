"""REST API for managing a book collection."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Book Collection API", version="1.0.0", lifespan=lifespan)


class BookIn(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: int | None = None
    isbn: str | None = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class Book(BookIn):
    id: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=201)
def create_book(book: BookIn):
    return db.create_book(book.title, book.author, book.year, book.isbn)


@app.get("/books", response_model=list[Book])
def list_books(author: str | None = None):
    return db.list_books(author)


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    book = db.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookIn):
    updated = db.update_book(book_id, book.title, book.author, book.year, book.isbn)
    if updated is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    if not db.delete_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found")
    return Response(status_code=204)
