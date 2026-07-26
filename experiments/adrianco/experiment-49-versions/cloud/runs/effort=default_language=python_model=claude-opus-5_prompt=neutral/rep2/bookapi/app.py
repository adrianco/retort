"""FastAPI application exposing the book collection."""

from __future__ import annotations

import os
import sqlite3
from typing import Annotated, Iterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bookapi import db, repository
from bookapi.repository import DuplicateIsbnError
from bookapi.schemas import Book, BookCreate, BookReplace, ErrorResponse, HealthResponse

ERROR_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    500: "internal_error",
    503: "service_unavailable",
}

ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse, "description": "Invalid request body or parameters"},
}
NOT_FOUND_RESPONSE: dict[int | str, dict] = {
    404: {"model": ErrorResponse, "description": "No book with that id"},
}
CONFLICT_RESPONSE: dict[int | str, dict] = {
    409: {"model": ErrorResponse, "description": "ISBN already used by another book"},
}

BookId = Annotated[int, Path(ge=1, description="Identifier returned when the book was created")]


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    """One connection per request, closed when the response has been produced."""
    conn = db.connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


# Annotations are deferred (PEP 563), so aliases used in route signatures must live
# at module level where FastAPI can resolve them.
Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
AuthorFilter = Annotated[
    Optional[str], Query(max_length=255, description="Case-insensitive exact match on the author")
]


def error_body(
    status_code: int,
    message: str,
    details: Optional[list[dict]] = None,
    code: Optional[str] = None,
) -> dict:
    return {
        "error": code or ERROR_CODES.get(status_code, "error"),
        "message": message,
        "details": details or [],
    }


def create_app(db_path: str | os.PathLike[str] | None = None) -> FastAPI:
    """Build the application. `db_path` overrides $BOOKS_DB_PATH (used by the tests)."""
    resolved_path = db.resolve_db_path(db_path)
    db.init_db(resolved_path)

    app = FastAPI(
        title="Book Collection API",
        description="Create, read, update and delete books stored in SQLite.",
        version="1.0.0",
    )
    app.state.db_path = resolved_path

    # ---------------------------------------------------------------- errors

    @app.exception_handler(RequestValidationError)
    def _on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": _field_name(err.get("loc", ())), "message": err.get("msg", "invalid value")}
            for err in exc.errors()
        ]
        # 400 rather than FastAPI's default 422: a malformed book is a bad request.
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_body(400, "Request validation failed", details, code="validation_error"),
        )

    @app.exception_handler(StarletteHTTPException)
    def _on_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.status_code, detail),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(DuplicateIsbnError)
    def _on_duplicate_isbn(request: Request, exc: DuplicateIsbnError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_body(409, str(exc), [{"field": "isbn", "message": "already in use"}]),
        )

    # ---------------------------------------------------------------- routes

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> Response:
        """Report whether the service and its database are usable."""
        try:
            conn = db.connect(app.state.db_path)
            try:
                repository.ping(conn)
            finally:
                conn.close()
        except sqlite3.Error as exc:  # pragma: no cover - needs a broken database file
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "degraded", "database": f"unavailable: {exc}"},
            )
        return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})

    @app.post(
        "/books",
        response_model=Book,
        status_code=status.HTTP_201_CREATED,
        responses={**ERROR_RESPONSES, **CONFLICT_RESPONSE},
        tags=["books"],
    )
    def create_book(payload: BookCreate, conn: Conn, response: Response) -> dict:
        """Add a book to the collection. `title` and `author` are required."""
        book = repository.create(conn, payload.model_dump())
        response.headers["Location"] = f"/books/{book['id']}"
        return book

    @app.get("/books", response_model=list[Book], responses=ERROR_RESPONSES, tags=["books"])
    def list_books(conn: Conn, author: AuthorFilter = None) -> list[dict]:
        """List books, optionally filtered by author."""
        if author is not None and not author.strip():
            author = None  # `?author=` with no value is treated as no filter
        return repository.list_books(conn, author)

    @app.get(
        "/books/{book_id}",
        response_model=Book,
        responses={**ERROR_RESPONSES, **NOT_FOUND_RESPONSE},
        tags=["books"],
    )
    def get_book(book_id: BookId, conn: Conn) -> dict:
        """Fetch a single book by id."""
        book = repository.get(conn, book_id)
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, _missing(book_id))
        return book

    @app.put(
        "/books/{book_id}",
        response_model=Book,
        responses={**ERROR_RESPONSES, **NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
        tags=["books"],
    )
    def update_book(book_id: BookId, payload: BookReplace, conn: Conn) -> dict:
        """Replace a book. Omitted optional fields (`year`, `isbn`) are cleared."""
        book = repository.replace(conn, book_id, payload.model_dump())
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, _missing(book_id))
        return book

    @app.delete(
        "/books/{book_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={**ERROR_RESPONSES, **NOT_FOUND_RESPONSE},
        tags=["books"],
    )
    def delete_book(book_id: BookId, conn: Conn) -> Response:
        """Remove a book from the collection."""
        if not repository.delete(conn, book_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, _missing(book_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


def _missing(book_id: int) -> str:
    return f"Book with id {book_id} not found"


def _field_name(loc: tuple) -> str:
    """Turn a pydantic location tuple into something a client can act on."""
    parts = [str(part) for part in loc]
    if parts and parts[0] in ("body", "query", "path"):
        named = parts[1:]
        # Malformed JSON reports a byte offset rather than a field: keep the section name.
        if named and not all(part.isdigit() for part in named):
            return ".".join(named)
        return parts[0]
    return ".".join(parts) or "request"
