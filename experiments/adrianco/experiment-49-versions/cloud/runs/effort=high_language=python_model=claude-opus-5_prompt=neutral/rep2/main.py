"""Book Collection REST API (FastAPI + SQLite).

Run with::

    uvicorn main:app --reload

Interactive docs are served at ``/docs``.
"""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Any, Iterator, Optional

from fastapi import Depends, FastAPI, Path, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

import database
from models import Book, BookCreate, BookPatch, BookUpdate, ErrorResponse

API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="Book Collection API",
    description="A small REST service for managing a collection of books.",
    version=API_VERSION,
    lifespan=lifespan,
)


def get_conn() -> Iterator[sqlite3.Connection]:
    """Per-request SQLite connection."""
    with database.get_connection() as conn:
        yield conn


Conn = Depends(get_conn)

_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Invalid input"},
    404: {"model": ErrorResponse, "description": "Book not found"},
    409: {"model": ErrorResponse, "description": "ISBN already in use"},
}


# --------------------------------------------------------------------------- #
# Error handling: one JSON shape for every failure.
# --------------------------------------------------------------------------- #

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Report validation problems as 400 with a field-by-field breakdown."""
    errors = []
    for err in exc.errors():
        location = [str(part) for part in err["loc"] if part not in ("body", "query", "path")]
        errors.append(
            {
                "field": ".".join(location) or "body",
                "message": err.get("msg", "invalid value"),
                "type": err.get("type", "value_error"),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"detail": "Validation failed", "errors": errors}),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


def _not_found(book_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Book with id {book_id} not found")


def _conflict(isbn: Optional[str]) -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT, f"A book with ISBN {isbn} already exists"
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/health", tags=["meta"], summary="Health check")
def health() -> JSONResponse:
    """Report service and database status."""
    try:
        with database.get_connection() as conn:
            database.ping(conn)
    except sqlite3.Error as exc:  # pragma: no cover - needs a broken database
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "database": "unavailable", "detail": str(exc)},
        )
    return JSONResponse(
        content={"status": "ok", "database": "ok", "version": API_VERSION}
    )


@app.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    responses=_ERRORS,
    tags=["books"],
    summary="Create a book",
)
def create_book(
    payload: BookCreate,
    response: Response,
    conn: sqlite3.Connection = Conn,
) -> dict[str, Any]:
    try:
        book = database.create_book(conn, payload.model_dump())
    except sqlite3.IntegrityError as exc:
        raise _conflict(payload.isbn) from exc
    response.headers["Location"] = f"/books/{book['id']}"
    return book


@app.get(
    "/books",
    response_model=list[Book],
    responses={400: _ERRORS[400]},
    tags=["books"],
    summary="List books",
)
def list_books(
    author: Optional[str] = Query(
        None, description="Case-insensitive partial match on the author name"
    ),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Max books to return"),
    offset: int = Query(0, ge=0, description="Number of books to skip"),
    conn: sqlite3.Connection = Conn,
) -> list[dict[str, Any]]:
    return database.list_books(conn, author=author, limit=limit, offset=offset)


@app.get(
    "/books/{book_id}",
    response_model=Book,
    responses=_ERRORS,
    tags=["books"],
    summary="Get a book",
)
def get_book(
    book_id: int = Path(..., ge=1),
    conn: sqlite3.Connection = Conn,
) -> dict[str, Any]:
    book = database.get_book(conn, book_id)
    if book is None:
        raise _not_found(book_id)
    return book


@app.put(
    "/books/{book_id}",
    response_model=Book,
    responses=_ERRORS,
    tags=["books"],
    summary="Replace a book",
)
def replace_book(
    payload: BookUpdate,
    book_id: int = Path(..., ge=1),
    conn: sqlite3.Connection = Conn,
) -> dict[str, Any]:
    try:
        book = database.replace_book(conn, book_id, payload.model_dump())
    except sqlite3.IntegrityError as exc:
        raise _conflict(payload.isbn) from exc
    if book is None:
        raise _not_found(book_id)
    return book


@app.patch(
    "/books/{book_id}",
    response_model=Book,
    responses=_ERRORS,
    tags=["books"],
    summary="Partially update a book",
)
def update_book(
    payload: BookPatch,
    book_id: int = Path(..., ge=1),
    conn: sqlite3.Connection = Conn,
) -> dict[str, Any]:
    try:
        book = database.update_book(conn, book_id, payload.changes())
    except sqlite3.IntegrityError as exc:
        raise _conflict(payload.isbn) from exc
    if book is None:
        raise _not_found(book_id)
    return book


@app.delete(
    "/books/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: _ERRORS[404]},
    tags=["books"],
    summary="Delete a book",
)
def delete_book(
    book_id: int = Path(..., ge=1),
    conn: sqlite3.Connection = Conn,
) -> Response:
    if not database.delete_book(conn, book_id):
        raise _not_found(book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
