"""A small WSGI REST API for managing a SQLite-backed book collection."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable, Iterable
from wsgiref.simple_server import make_server


DEFAULT_DB_PATH = "books.db"


def create_app(database_path: str | os.PathLike[str] = DEFAULT_DB_PATH) -> Callable:
    """Create the application and ensure its database schema exists."""
    database_path = str(database_path)
    _initialize_database(database_path)

    def application(environ: dict[str, Any], start_response: Callable) -> Iterable[bytes]:
        try:
            return _dispatch(environ, start_response, database_path)
        except Exception:  # Do not expose implementation details to API clients.
            return _json_response(start_response, 500, {"error": "Internal server error"})

    return application


def _initialize_database(database_path: str) -> None:
    parent = Path(database_path).parent
    parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
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


def _dispatch(environ: dict[str, Any], start_response: Callable, database_path: str) -> Iterable[bytes]:
    method = environ["REQUEST_METHOD"].upper()
    path = environ.get("PATH_INFO", "") or "/"

    if method == "GET" and path == "/health":
        return _json_response(start_response, 200, {"status": "ok"})

    if path == "/books":
        if method == "POST":
            return _create_book(environ, start_response, database_path)
        if method == "GET":
            return _list_books(environ, start_response, database_path)
        return _method_not_allowed(start_response, "GET, POST")

    book_id = _book_id_from_path(path)
    if book_id is not None:
        if method == "GET":
            return _get_book(start_response, database_path, book_id)
        if method == "PUT":
            return _update_book(environ, start_response, database_path, book_id)
        if method == "DELETE":
            return _delete_book(start_response, database_path, book_id)
        return _method_not_allowed(start_response, "GET, PUT, DELETE")

    return _json_response(start_response, 404, {"error": "Not found"})


def _book_id_from_path(path: str) -> int | None:
    pieces = path.strip("/").split("/")
    if len(pieces) != 2 or pieces[0] != "books":
        return None
    try:
        book_id = int(pieces[1])
    except ValueError:
        return None
    return book_id if book_id > 0 else None


def _create_book(environ: dict[str, Any], start_response: Callable, database_path: str) -> Iterable[bytes]:
    payload, error = _read_and_validate_book(environ)
    if error:
        return _json_response(start_response, 400, {"error": error})

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (payload["title"], payload["author"], payload["year"], payload["isbn"]),
        )
        book = _fetch_book(connection, cursor.lastrowid)
    return _json_response(start_response, 201, book, {"Location": f"/books/{book['id']}"})


def _list_books(environ: dict[str, Any], start_response: Callable, database_path: str) -> Iterable[bytes]:
    from urllib.parse import parse_qs

    author_values = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True).get("author")
    author = author_values[-1] if author_values else None
    query = "SELECT id, title, author, year, isbn FROM books"
    parameters: tuple[str, ...] = ()
    if author is not None:
        query += " WHERE author = ?"
        parameters = (author,)
    query += " ORDER BY id"
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return _json_response(start_response, 200, [_row_to_book(row) for row in rows])


def _get_book(start_response: Callable, database_path: str, book_id: int) -> Iterable[bytes]:
    with sqlite3.connect(database_path) as connection:
        book = _fetch_book(connection, book_id)
    return _json_response(start_response, 200, book) if book else _not_found(start_response)


def _update_book(environ: dict[str, Any], start_response: Callable, database_path: str, book_id: int) -> Iterable[bytes]:
    payload, error = _read_and_validate_book(environ)
    if error:
        return _json_response(start_response, 400, {"error": error})
    with sqlite3.connect(database_path) as connection:
        updated = connection.execute(
            "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
            (payload["title"], payload["author"], payload["year"], payload["isbn"], book_id),
        ).rowcount
        book = _fetch_book(connection, book_id) if updated else None
    return _json_response(start_response, 200, book) if book else _not_found(start_response)


def _delete_book(start_response: Callable, database_path: str, book_id: int) -> Iterable[bytes]:
    with sqlite3.connect(database_path) as connection:
        deleted = connection.execute("DELETE FROM books WHERE id = ?", (book_id,)).rowcount
    if not deleted:
        return _not_found(start_response)
    return _empty_response(start_response, 204)


def _read_and_validate_book(environ: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if environ.get("CONTENT_TYPE", "").split(";", 1)[0].lower() != "application/json":
        return None, "Content-Type must be application/json"
    try:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(content_length)
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None, "Request body must be valid JSON"
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    title, author = data.get("title"), data.get("author")
    if not isinstance(title, str) or not title.strip():
        return None, "title is required and must be a non-empty string"
    if not isinstance(author, str) or not author.strip():
        return None, "author is required and must be a non-empty string"

    year = data.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
        return None, "year must be an integer or null"
    isbn = data.get("isbn")
    if isbn is not None and not isinstance(isbn, str):
        return None, "isbn must be a string or null"
    return {"title": title.strip(), "author": author.strip(), "year": year, "isbn": isbn}, None


def _fetch_book(connection: sqlite3.Connection, book_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT id, title, author, year, isbn FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    return _row_to_book(row) if row else None


def _row_to_book(row: tuple[Any, ...]) -> dict[str, Any]:
    return dict(zip(("id", "title", "author", "year", "isbn"), row, strict=True))


def _json_response(start_response: Callable, status: int, payload: Any, extra_headers: dict[str, str] | None = None) -> Iterable[bytes]:
    body = json.dumps(payload).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
    if extra_headers:
        headers.extend(extra_headers.items())
    start_response(f"{status} {_reason_phrase(status)}", headers)
    return [body]


def _empty_response(start_response: Callable, status: int) -> Iterable[bytes]:
    start_response(f"{status} {_reason_phrase(status)}", [("Content-Length", "0")])
    return [b""]


def _not_found(start_response: Callable) -> Iterable[bytes]:
    return _json_response(start_response, 404, {"error": "Book not found"})


def _method_not_allowed(start_response: Callable, allowed: str) -> Iterable[bytes]:
    return _json_response(start_response, 405, {"error": "Method not allowed"}, {"Allow": allowed})


def _reason_phrase(status: int) -> str:
    return {200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"}[status]


app = create_app(os.environ.get("BOOKS_DB", DEFAULT_DB_PATH))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving book API on http://127.0.0.1:{port}")
    make_server("127.0.0.1", port, app).serve_forever()
