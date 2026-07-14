"""Book collection REST API using Python stdlib only."""
from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterator
from urllib.parse import parse_qs, urlsplit

DEFAULT_DB_PATH = "books.db"
DEFAULT_PORT = 8000


@contextmanager
def get_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
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


def book_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"],
    }


def validate_book_payload(payload: Any, *, partial: bool = False) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object"

    cleaned: dict[str, Any] = {}
    allowed = {"title", "author", "year", "isbn"}
    unknown = set(payload) - allowed
    if unknown:
        return None, f"Unknown fields: {', '.join(sorted(unknown))}"

    if not partial:
        for required in ("title", "author"):
            value = payload.get(required)
            if not isinstance(value, str) or not value.strip():
                return None, f"'{required}' is required and must be a non-empty string"
            cleaned[required] = value.strip()
    else:
        for field in ("title", "author"):
            if field in payload:
                value = payload[field]
                if not isinstance(value, str) or not value.strip():
                    return None, f"'{field}' must be a non-empty string"
                cleaned[field] = value.strip()

    if "year" in payload:
        year = payload["year"]
        if year is not None and not isinstance(year, int):
            return None, "'year' must be an integer or null"
        if isinstance(year, bool):
            return None, "'year' must be an integer or null"
        cleaned["year"] = year
    elif not partial:
        cleaned["year"] = None

    if "isbn" in payload:
        isbn = payload["isbn"]
        if isbn is not None and not isinstance(isbn, str):
            return None, "'isbn' must be a string or null"
        cleaned["isbn"] = isbn
    elif not partial:
        cleaned["isbn"] = None

    return cleaned, None


def make_handler(db_path: str) -> type[BaseHTTPRequestHandler]:
    class BookHandler(BaseHTTPRequestHandler):
        server_version = "BookAPI/1.0"

        def log_message(self, format: str, *args: Any) -> None:  # quieter logs
            return

        def _send_json(self, status: int, body: Any) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json_body(self) -> tuple[Any, str | None]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return None, "Request body is required"
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8")), None
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None, "Invalid JSON in request body"

        def _parse_book_id(self, segment: str) -> int | None:
            try:
                book_id = int(segment)
            except ValueError:
                return None
            return book_id if book_id > 0 else None

        def _route(self) -> tuple[str, list[str], dict[str, list[str]]]:
            parts = urlsplit(self.path)
            path = parts.path.rstrip("/") or "/"
            segments = [s for s in path.split("/") if s]
            query = parse_qs(parts.query)
            return path, segments, query

        def do_GET(self) -> None:
            _, segments, query = self._route()
            if segments == ["health"]:
                self._send_json(200, {"status": "ok"})
                return
            if segments == ["books"]:
                self._list_books(query)
                return
            if len(segments) == 2 and segments[0] == "books":
                book_id = self._parse_book_id(segments[1])
                if book_id is None:
                    self._send_json(400, {"error": "Invalid book id"})
                    return
                self._get_book(book_id)
                return
            self._send_json(404, {"error": "Not found"})

        def do_POST(self) -> None:
            _, segments, _ = self._route()
            if segments == ["books"]:
                self._create_book()
                return
            self._send_json(404, {"error": "Not found"})

        def do_PUT(self) -> None:
            _, segments, _ = self._route()
            if len(segments) == 2 and segments[0] == "books":
                book_id = self._parse_book_id(segments[1])
                if book_id is None:
                    self._send_json(400, {"error": "Invalid book id"})
                    return
                self._update_book(book_id)
                return
            self._send_json(404, {"error": "Not found"})

        def do_DELETE(self) -> None:
            _, segments, _ = self._route()
            if len(segments) == 2 and segments[0] == "books":
                book_id = self._parse_book_id(segments[1])
                if book_id is None:
                    self._send_json(400, {"error": "Invalid book id"})
                    return
                self._delete_book(book_id)
                return
            self._send_json(404, {"error": "Not found"})

        def _list_books(self, query: dict[str, list[str]]) -> None:
            with get_connection(db_path) as conn:
                if "author" in query and query["author"]:
                    rows = conn.execute(
                        "SELECT * FROM books WHERE author = ? ORDER BY id",
                        (query["author"][0],),
                    ).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM books ORDER BY id").fetchall()
            self._send_json(200, [book_to_dict(r) for r in rows])

        def _get_book(self, book_id: int) -> None:
            with get_connection(db_path) as conn:
                row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            if row is None:
                self._send_json(404, {"error": "Book not found"})
                return
            self._send_json(200, book_to_dict(row))

        def _create_book(self) -> None:
            payload, err = self._read_json_body()
            if err is not None:
                self._send_json(400, {"error": err})
                return
            data, verr = validate_book_payload(payload, partial=False)
            if verr is not None:
                self._send_json(400, {"error": verr})
                return
            assert data is not None
            with get_connection(db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                    (data["title"], data["author"], data["year"], data["isbn"]),
                )
                new_id = cursor.lastrowid
                row = conn.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
            self._send_json(201, book_to_dict(row))

        def _update_book(self, book_id: int) -> None:
            payload, err = self._read_json_body()
            if err is not None:
                self._send_json(400, {"error": err})
                return
            data, verr = validate_book_payload(payload, partial=True)
            if verr is not None:
                self._send_json(400, {"error": verr})
                return
            assert data is not None
            with get_connection(db_path) as conn:
                existing = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
                if existing is None:
                    self._send_json(404, {"error": "Book not found"})
                    return
                if not data:
                    self._send_json(200, book_to_dict(existing))
                    return
                set_clause = ", ".join(f"{field} = ?" for field in data)
                values = list(data.values()) + [book_id]
                conn.execute(f"UPDATE books SET {set_clause} WHERE id = ?", values)
                row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            self._send_json(200, book_to_dict(row))

        def _delete_book(self, book_id: int) -> None:
            with get_connection(db_path) as conn:
                cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
                if cursor.rowcount == 0:
                    self._send_json(404, {"error": "Book not found"})
                    return
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

    return BookHandler


def run(host: str = "127.0.0.1", port: int = DEFAULT_PORT, db_path: str = DEFAULT_DB_PATH) -> None:
    init_db(db_path)
    handler = make_handler(db_path)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Book API listening on http://{host}:{port} (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run(port=port)
