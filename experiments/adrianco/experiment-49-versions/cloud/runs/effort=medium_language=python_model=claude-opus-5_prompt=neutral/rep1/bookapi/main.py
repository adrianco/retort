"""REST API for managing a book collection."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response, status

from .db import get_conn, init_db, row_to_dict
from .schemas import Book, BookIn, ErrorResponse

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Book not found"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "ISBN already exists"}}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Book Collection API",
    version="1.0.0",
    description="CRUD service for a book collection backed by SQLite.",
    lifespan=lifespan,
)


def _fetch_book(conn: sqlite3.Connection, book_id: int) -> dict:
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found",
        )
    return row_to_dict(row)


def _raise_isbn_conflict(exc: sqlite3.IntegrityError, isbn: str | None) -> None:
    """Translate a UNIQUE(isbn) violation into a 409; re-raise anything else."""
    if "books.isbn" in str(exc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A book with isbn {isbn!r} already exists",
        ) from exc
    raise exc


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness probe; also verifies the database is reachable."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unavailable: {exc}",
        ) from exc
    return {"status": "ok"}


@app.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT,
    tags=["books"],
)
def create_book(payload: BookIn, response: Response) -> Book:
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                (payload.title, payload.author, payload.year, payload.isbn),
            )
        except sqlite3.IntegrityError as exc:
            _raise_isbn_conflict(exc, payload.isbn)
        book_id = cur.lastrowid
    response.headers["Location"] = f"/books/{book_id}"
    return Book(id=book_id, **payload.model_dump())


@app.get("/books", response_model=list[Book], tags=["books"])
def list_books(
    author: str | None = Query(default=None, description="Exact author match"),
) -> list[Book]:
    sql = "SELECT * FROM books"
    params: tuple = ()
    if author is not None:
        sql += " WHERE author = ?"
        params = (author.strip(),)
    sql += " ORDER BY id"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Book(**row_to_dict(r)) for r in rows]


@app.get("/books/{book_id}", response_model=Book, responses=NOT_FOUND, tags=["books"])
def get_book(book_id: int) -> Book:
    with get_conn() as conn:
        return Book(**_fetch_book(conn, book_id))


@app.put(
    "/books/{book_id}",
    response_model=Book,
    responses={**NOT_FOUND, **CONFLICT},
    tags=["books"],
)
def update_book(book_id: int, payload: BookIn) -> Book:
    with get_conn() as conn:
        _fetch_book(conn, book_id)  # 404 before attempting the write
        try:
            conn.execute(
                "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
                (payload.title, payload.author, payload.year, payload.isbn, book_id),
            )
        except sqlite3.IntegrityError as exc:
            _raise_isbn_conflict(exc, payload.isbn)
    return Book(id=book_id, **payload.model_dump())


@app.delete(
    "/books/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND,
    tags=["books"],
)
def delete_book(book_id: int) -> Response:
    with get_conn() as conn:
        _fetch_book(conn, book_id)
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
