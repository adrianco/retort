"""REST API service for managing a book collection.

Built with FastAPI + SQLite.
"""

import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

import db

DB_PATH = os.environ.get("BOOKS_DB_PATH", db.DEFAULT_DB_PATH)


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class BookIn(BaseModel):
    title: str = Field(..., description="Book title (required)")
    author: str = Field(..., description="Book author (required)")
    year: Optional[int] = Field(None, description="Publication year")
    isbn: Optional[str] = Field(None, description="ISBN")

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class Book(BookIn):
    id: int


# --------------------------------------------------------------------------- #
# App factory
# --------------------------------------------------------------------------- #
def create_app(db_path: str = DB_PATH) -> FastAPI:
    app = FastAPI(title="Book Collection API", version="1.0.0")
    db.init_db(db_path)

    def get_db():
        with db.get_conn(db_path) as conn:
            yield conn

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/books", response_model=Book, status_code=201)
    def create_book(book: BookIn, conn=Depends(get_db)):
        return db.create_book(conn, book.title, book.author, book.year, book.isbn)

    @app.get("/books", response_model=list[Book])
    def list_books(
        author: Optional[str] = Query(None, description="Filter by author"),
        conn=Depends(get_db),
    ):
        return db.list_books(conn, author)

    @app.get("/books/{book_id}", response_model=Book)
    def get_book(book_id: int, conn=Depends(get_db)):
        book = db.get_book(conn, book_id)
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    @app.put("/books/{book_id}", response_model=Book)
    def update_book(book_id: int, book: BookIn, conn=Depends(get_db)):
        updated = db.update_book(
            conn, book_id, book.title, book.author, book.year, book.isbn
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return updated

    @app.delete("/books/{book_id}", status_code=204)
    def delete_book(book_id: int, conn=Depends(get_db)):
        if not db.delete_book(conn, book_id):
            raise HTTPException(status_code=404, detail="Book not found")
        return JSONResponse(status_code=204, content=None)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
