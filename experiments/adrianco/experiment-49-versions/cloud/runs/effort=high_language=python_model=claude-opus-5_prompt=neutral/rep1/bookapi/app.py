"""WSGI application: routing, request parsing and JSON responses."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs

from .db import BookNotFound, Database
from .validation import ValidationError, parse_book

JSON_CONTENT_TYPE = "application/json"
MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MiB is plenty for a book record.

StartResponse = Callable[[str, list[tuple[str, str]]], Any]

_BOOK_ID_PATH = re.compile(r"^/books/([^/]+)$")

_STATUS_TEXT = {
    200: "200 OK",
    201: "201 Created",
    204: "204 No Content",
    400: "400 Bad Request",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    413: "413 Payload Too Large",
    415: "415 Unsupported Media Type",
    500: "500 Internal Server Error",
    503: "503 Service Unavailable",
}


class HTTPError(Exception):
    """An error that maps directly onto a JSON response."""

    def __init__(self, status: int, message: str, details: Any = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


class BookAPI:
    """The book collection API as a WSGI callable."""

    def __init__(self, db: Database):
        self.db = db

    def __call__(
        self, environ: dict[str, Any], start_response: StartResponse
    ) -> Iterable[bytes]:
        try:
            status, payload, headers = self._dispatch(environ)
        except HTTPError as exc:
            status, payload, headers = exc.status, _error_body(exc), []
            if status == 405:
                headers.append(("Allow", ", ".join(exc.details["allowed"])))
        except ValidationError as exc:
            status = 400
            payload = {"error": exc.message, "details": exc.errors}
            headers = []
        except Exception:  # pragma: no cover - defensive catch-all
            environ["wsgi.errors"].write("Unhandled error in BookAPI\n")
            status, payload, headers = 500, {"error": "Internal server error."}, []

        head_request = environ.get("REQUEST_METHOD", "GET").upper() == "HEAD"
        return _respond(start_response, status, payload, headers, head_request)

    # -- routing --------------------------------------------------------

    def _dispatch(
        self, environ: dict[str, Any]
    ) -> tuple[int, Any, list[tuple[str, str]]]:
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = _normalise_path(environ.get("PATH_INFO", "/"))

        if path == "/health":
            _require_method(method, ("GET", "HEAD"))
            return self._health()

        if path == "/books":
            _require_method(method, ("GET", "POST"))
            if method == "POST":
                return self._create(environ)
            return self._list(environ)

        match = _BOOK_ID_PATH.match(path)
        if match:
            _require_method(method, ("GET", "PUT", "DELETE"))
            book_id = _parse_book_id(match.group(1))
            if method == "GET":
                return self._get(book_id)
            if method == "PUT":
                return self._update(book_id, environ)
            return self._delete(book_id)

        raise HTTPError(404, f"No route for {path}.")

    # -- handlers -------------------------------------------------------

    def _health(self) -> tuple[int, Any, list[tuple[str, str]]]:
        healthy = self.db.ping()
        body = {
            "status": "ok" if healthy else "unhealthy",
            "database": "ok" if healthy else "unavailable",
        }
        return (200 if healthy else 503), body, []

    def _create(self, environ: dict[str, Any]) -> tuple[int, Any, list[tuple[str, str]]]:
        book = self.db.create(parse_book(_read_json(environ)))
        return 201, book, [("Location", f"/books/{book['id']}")]

    def _list(self, environ: dict[str, Any]) -> tuple[int, Any, list[tuple[str, str]]]:
        query = parse_qs(environ.get("QUERY_STRING", ""))
        author = query.get("author", [None])[0]
        return 200, self.db.list(author=author), []

    def _get(self, book_id: int) -> tuple[int, Any, list[tuple[str, str]]]:
        book = self.db.get(book_id)
        if book is None:
            raise HTTPError(404, f"Book {book_id} not found.")
        return 200, book, []

    def _update(
        self, book_id: int, environ: dict[str, Any]
    ) -> tuple[int, Any, list[tuple[str, str]]]:
        book = parse_book(_read_json(environ))
        try:
            return 200, self.db.update(book_id, book), []
        except BookNotFound:
            raise HTTPError(404, f"Book {book_id} not found.") from None

    def _delete(self, book_id: int) -> tuple[int, Any, list[tuple[str, str]]]:
        try:
            self.db.delete(book_id)
        except BookNotFound:
            raise HTTPError(404, f"Book {book_id} not found.") from None
        return 204, None, []


def create_app(db_path: str = "books.db") -> BookAPI:
    """Build the WSGI application backed by the SQLite database at ``db_path``."""
    return BookAPI(Database(db_path))


# -- request/response helpers -------------------------------------------


def _normalise_path(path: str) -> str:
    if not path:
        return "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"
    return path


def _require_method(method: str, allowed: tuple[str, ...]) -> None:
    if method not in allowed:
        raise HTTPError(
            405,
            f"Method {method} is not allowed here.",
            {"allowed": list(allowed)},
        )


def _parse_book_id(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise HTTPError(404, f"Book {raw!r} not found.") from None


def _read_json(environ: dict[str, Any]) -> Any:
    content_type = environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower()
    if content_type and content_type != JSON_CONTENT_TYPE:
        raise HTTPError(415, f"Content-Type must be {JSON_CONTENT_TYPE}.")

    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        raise HTTPError(400, "Invalid Content-Length header.") from None
    if length < 0:
        raise HTTPError(400, "Invalid Content-Length header.")
    if length > MAX_BODY_BYTES:
        raise HTTPError(413, "Request body is too large.")

    raw = environ["wsgi.input"].read(length) if length else b""
    if not raw.strip():
        raise HTTPError(400, "Request body must not be empty.")

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPError(400, f"Request body is not valid JSON: {exc}.") from None


def _error_body(exc: HTTPError) -> dict[str, Any]:
    body: dict[str, Any] = {"error": exc.message}
    if exc.details is not None:
        body["details"] = exc.details
    return body


def _respond(
    start_response: StartResponse,
    status: int,
    payload: Any,
    headers: list[tuple[str, str]],
    head_request: bool = False,
) -> list[bytes]:
    body = b""
    if status != 204 and payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    response_headers = [("Content-Length", str(len(body)))] + headers
    if body:
        response_headers.insert(
            0, ("Content-Type", f"{JSON_CONTENT_TYPE}; charset=utf-8")
        )

    start_response(_STATUS_TEXT.get(status, f"{status} Status"), response_headers)
    # A HEAD response carries the headers of the equivalent GET but no body.
    return [b""] if head_request else [body]
