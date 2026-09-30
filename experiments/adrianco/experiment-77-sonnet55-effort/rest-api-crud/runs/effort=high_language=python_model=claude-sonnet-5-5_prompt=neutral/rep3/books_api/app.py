"""WSGI application: routing, validation and JSON handling."""

import json
import re
from http import HTTPStatus
from urllib.parse import parse_qs

from .store import BookStore, DuplicateISBN

MAX_BODY = 1024 * 1024
BOOK_PATH = re.compile(r"^/books/(\d+)/?$")


class HTTPError(Exception):
    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def validate_book(data):
    """Return (title, author, year, isbn) or raise HTTPError(422)."""
    if not isinstance(data, dict):
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object")

    errors = {}
    values = {}
    for field in ("title", "author"):
        v = data.get(field)
        if not isinstance(v, str) or not v.strip():
            errors[field] = "is required and must be a non-empty string"
        else:
            values[field] = v.strip()

    year = data.get("year")
    if year is not None and (
        isinstance(year, bool) or not isinstance(year, int) or not -9999 <= year <= 9999
    ):
        errors["year"] = "must be an integer"

    isbn = data.get("isbn")
    if isbn is not None:
        if not isinstance(isbn, str) or not isbn.strip():
            errors["isbn"] = "must be a non-empty string"
        else:
            isbn = isbn.strip()

    if errors:
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Validation failed", errors)
    return values["title"], values["author"], year, isbn


def create_app(store=None):
    """Build a WSGI callable backed by `store` (default: in-memory SQLite)."""
    store = store or BookStore()

    def read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
        if length > MAX_BODY:
            raise HTTPError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Body too large")
        raw = environ["wsgi.input"].read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(HTTPStatus.BAD_REQUEST, "Request body must be valid JSON")

    def get_or_404(book_id):
        book = store.get(book_id)
        if book is None:
            raise HTTPError(HTTPStatus.NOT_FOUND, f"Book {book_id} not found")
        return book

    def dispatch(environ):
        method, path = environ["REQUEST_METHOD"], environ["PATH_INFO"]

        if path == "/health":
            if method != "GET":
                raise HTTPError(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed")
            store.ping()
            return HTTPStatus.OK, {"status": "ok"}

        if path.rstrip("/") == "/books":
            if method == "POST":
                try:
                    book = store.create(*validate_book(read_json(environ)))
                except DuplicateISBN:
                    raise HTTPError(HTTPStatus.CONFLICT, "ISBN already exists")
                return HTTPStatus.CREATED, book
            if method == "GET":
                query = parse_qs(environ.get("QUERY_STRING", ""))
                author = query.get("author", [None])[0]
                return HTTPStatus.OK, store.list(author)
            raise HTTPError(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed")

        m = BOOK_PATH.match(path)
        if m:
            book_id = int(m.group(1))
            if method == "GET":
                return HTTPStatus.OK, get_or_404(book_id)
            if method == "PUT":
                get_or_404(book_id)
                fields = validate_book(read_json(environ))
                try:
                    book = store.update(book_id, *fields)
                except DuplicateISBN:
                    raise HTTPError(HTTPStatus.CONFLICT, "ISBN already exists")
                if book is None:  # deleted concurrently
                    raise HTTPError(HTTPStatus.NOT_FOUND, f"Book {book_id} not found")
                return HTTPStatus.OK, book
            if method == "DELETE":
                get_or_404(book_id)
                store.delete(book_id)
                return HTTPStatus.NO_CONTENT, None
            raise HTTPError(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed")

        raise HTTPError(HTTPStatus.NOT_FOUND, "Not found")

    def app(environ, start_response):
        try:
            status, payload = dispatch(environ)
        except HTTPError as err:
            status = err.status
            payload = {"error": err.message}
            if err.details:
                payload["details"] = err.details
        except Exception:  # pragma: no cover - last-resort guard
            status, payload = HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"}

        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        headers = [("Content-Length", str(len(body)))]
        if body:
            headers.append(("Content-Type", "application/json"))
        start_response(f"{status.value} {status.phrase}", headers)
        return [body]

    return app
