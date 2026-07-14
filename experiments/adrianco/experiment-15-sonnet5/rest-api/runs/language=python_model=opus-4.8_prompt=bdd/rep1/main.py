"""REST API service for managing a book collection (FastAPI + SQLite)."""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from db import Database

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BookIn(BaseModel):
    """Payload for creating or updating a book.

    `title` and `author` are required; `min_length=1` rejects empty strings.
    """

    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookOut(BookIn):
    id: int


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(db: Optional[Database] = None) -> FastAPI:
    """Build the FastAPI app. A custom `db` can be injected for tests."""

    app = FastAPI(title="Book Collection API")
    database = db if db is not None else Database()

    def get_db() -> Database:
        return database

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/books", response_model=BookOut, status_code=201)
    def create_book(book: BookIn, database: Database = Depends(get_db)):
        return database.create_book(book.title, book.author, book.year, book.isbn)

    @app.get("/books", response_model=list[BookOut])
    def list_books(author: Optional[str] = None, database: Database = Depends(get_db)):
        return database.list_books(author=author)

    @app.get("/books/{book_id}", response_model=BookOut)
    def get_book(book_id: int, database: Database = Depends(get_db)):
        book = database.get_book(book_id)
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    @app.put("/books/{book_id}", response_model=BookOut)
    def update_book(book_id: int, book: BookIn, database: Database = Depends(get_db)):
        updated = database.update_book(
            book_id, book.title, book.author, book.year, book.isbn
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return updated

    @app.delete("/books/{book_id}", status_code=204)
    def delete_book(book_id: int, database: Database = Depends(get_db)):
        if not database.delete_book(book_id):
            raise HTTPException(status_code=404, detail="Book not found")
        return None

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
