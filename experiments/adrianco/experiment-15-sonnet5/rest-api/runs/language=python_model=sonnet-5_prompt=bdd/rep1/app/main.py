import sqlite3
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response

from app.database import DEFAULT_DB_PATH, get_connection, init_db
from app.schemas import BookCreate, BookResponse, BookUpdate

app = FastAPI(title="Book Collection API")


def get_db():
    conn = get_connection(DEFAULT_DB_PATH)
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()


def _row_to_book(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/books", response_model=BookResponse, status_code=201)
def create_book(book: BookCreate, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (book.title, book.author, book.year, book.isbn),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_book(row)


@app.get("/books", response_model=list[BookResponse])
def list_books(
    author: Optional[str] = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db),
):
    if author is not None:
        rows = conn.execute(
            "SELECT * FROM books WHERE author LIKE ? COLLATE NOCASE",
            (f"%{author}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books").fetchall()
    return [_row_to_book(row) for row in rows]


@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return _row_to_book(row)


@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int, book: BookUpdate, conn: sqlite3.Connection = Depends(get_db)
):
    existing = conn.execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail="Book not found")
    conn.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (book.title, book.author, book.year, book.isbn, book_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return _row_to_book(row)


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int, conn: sqlite3.Connection = Depends(get_db)):
    existing = conn.execute(
        "SELECT * FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail="Book not found")
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    return Response(status_code=204)
