import sqlite3
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DB_PATH = "books.db"


def init_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        """
    )
    conn.commit()
    conn.close()


@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class BookIn(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookOut(BookIn):
    id: int


def row_to_book(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def create_app(db_path: str = DB_PATH) -> FastAPI:
    init_db(db_path)
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/books", status_code=201)
    def create_book(book: BookIn):
        with get_conn(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (book.title, book.author, book.year, book.isbn),
            )
            book_id = cur.lastrowid
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return row_to_book(row)

    @app.get("/books")
    def list_books(author: Optional[str] = Query(None)):
        with get_conn(db_path) as conn:
            if author:
                rows = conn.execute(
                    "SELECT * FROM books WHERE author = ?", (author,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM books").fetchall()
            return [row_to_book(r) for r in rows]

    @app.get("/books/{book_id}")
    def get_book(book_id: int):
        with get_conn(db_path) as conn:
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Book not found")
            return row_to_book(row)

    @app.put("/books/{book_id}")
    def update_book(book_id: int, book: BookIn):
        with get_conn(db_path) as conn:
            existing = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if existing is None:
                raise HTTPException(status_code=404, detail="Book not found")
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (book.title, book.author, book.year, book.isbn, book_id),
            )
            row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return row_to_book(row)

    @app.delete("/books/{book_id}", status_code=204)
    def delete_book(book_id: int):
        with get_conn(db_path) as conn:
            existing = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if existing is None:
                raise HTTPException(status_code=404, detail="Book not found")
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            return None

    return app


app = create_app()
